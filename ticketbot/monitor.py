import asyncio
import logging
import time
import discord
from ticketbot.metrics import TICKETS_OPEN, TICKETS_STALE
from ticketbot import db

log = logging.getLogger(__name__)


class StaleTicketMonitor:
    def __init__(self, bot: discord.Client, db_path: str, interval_sec: int = 300, stale_after_hours: int = 24):
        self.bot = bot
        self.db_path = db_path
        self.interval = interval_sec
        self.stale_threshold = stale_after_hours * 3600
        self._task: asyncio.Task | None = None
        self._running = False
        self._known_categories: set[str] = set()

    def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="stale-ticket-monitor")

    async def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        # wait until gateway handshake finishes so channel fetches actually work
        await self.bot.wait_until_ready()
        while self._running:
            try:
                await self.check_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.exception("stale monitor iteration failed: %s", e)

            try:
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break

    async def check_once(self):
        now = int(time.time())
        cutoff = now - self.stale_threshold
        open_tickets = await db.get_open_tickets(self.db_path)

        cat_counts: dict[str, int] = {}
        stale_count = 0
        # t0 = time.monotonic()

        for t in open_tickets:
            cat = t.get("category") or "general"
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

            last_act = t["last_message_at"] or t["created_at"]
            if last_act < cutoff:
                stale_count += 1
                # only ping once every 24h per ticket to avoid spamming the user
                last_warned = t.get("last_stale_warning_at") or 0
                if now - last_warned >= self.stale_threshold:
                    await self._notify_stale_ticket(t)

        # zero out stale categories that no longer have open tickets
        current_cats = set(cat_counts.keys())
        for dead_cat in self._known_categories - current_cats:
            TICKETS_OPEN.labels(category=dead_cat).set(0)
        self._known_categories = current_cats

        for cat, count in cat_counts.items():
            TICKETS_OPEN.labels(category=cat).set(count)
        TICKETS_STALE.set(stale_count)

        # print(f"stale ticket check took {time.monotonic() - t0:.3f}s")

    async def _notify_stale_ticket(self, ticket_row: dict):
        ch_id = ticket_row.get("channel_id")
        if not ch_id:
            return

        channel = self.bot.get_channel(ch_id)
        if not channel:
            try:
                # fallback to REST api if channel isn't in gateway cache
                channel = await self.bot.fetch_channel(ch_id)
            except (discord.NotFound, discord.Forbidden):
                # channel got deleted manually outside the bot
                log.warning("ticket %s channel %s missing, closing in db", ticket_row["id"], ch_id)
                await db.close_ticket(self.db_path, ticket_row["id"], closed_by=0, reason="channel_deleted")
                return

        if not isinstance(channel, discord.TextChannel):
            return

        # TODO(alex): batch channel fetch instead of hitting rest api one by one if guild has >50 stale
        embed = discord.Embed(
            title="Ticket Inactivity Warning",
            description="This ticket has had no activity for over 24 hours. If your issue is resolved, please click **Close Ticket** below.",
            color=discord.Color.gold(),
        )
        try:
            await channel.send(embed=embed)
            await db.update_ticket_stale_warning(self.db_path, ticket_row["id"], int(time.time()))
        except discord.HTTPException as err:
            log.error("failed sending stale reminder to %s: %s", ch_id, err)
