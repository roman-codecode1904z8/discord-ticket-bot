import datetime
from pathlib import Path
from typing import Any, Optional
import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMP NOT NULL,
    first_response_at TIMESTAMP,
    closed_at TIMESTAMP,
    closed_by INTEGER,
    close_reason TEXT,
    claimed_by INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id);
"""


class Database:
    """Handles ticket persistence and lightweight schema migration checks."""

    def __init__(self, path: Path | str):
        self.path = str(path)
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA foreign_keys=ON;")
        await self._conn.executescript(SCHEMA)
        await self._run_migrations()
        await self._conn.commit()

    async def _run_migrations(self):
        async with self.conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
            current_ver = row["version"] if row else 0

        if current_ver < 1:
            # verify claimed_by exists for databases initialized before revision 39
            async with self.conn.execute("PRAGMA table_info(tickets)") as cur:
                cols = [r["name"] for r in await cur.fetchall()]
                if "claimed_by" not in cols:
                    await self.conn.execute("ALTER TABLE tickets ADD COLUMN claimed_by INTEGER;")

            await self.conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (1);")

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._conn

    async def create_ticket(self, channel_id: int, user_id: int) -> int:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor = await self.conn.execute(
            """
            INSERT INTO tickets (channel_id, user_id, status, created_at)
            VALUES (?, ?, 'open', ?)
            """,
            (channel_id, user_id, now),
        )
        await self.conn.commit()
        return cursor.lastrowid

    async def get_ticket_by_channel(self, channel_id: int) -> Optional[dict[str, Any]]:
        async with self.conn.execute(
            "SELECT * FROM tickets WHERE channel_id = ?", (channel_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def mark_first_response(self, channel_id: int) -> bool:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        # only update on the initial staff reply
        cursor = await self.conn.execute(
            """
            UPDATE tickets
            SET first_response_at = ?
            WHERE channel_id = ? AND first_response_at IS NULL AND status = 'open'
            """,
            (now, channel_id),
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def claim_ticket(self, channel_id: int, user_id: int) -> bool:
        cursor = await self.conn.execute(
            """
            UPDATE tickets
            SET claimed_by = ?
            WHERE channel_id = ? AND status = 'open' AND claimed_by IS NULL
            """,
            (user_id, channel_id),
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def close_ticket(
        self,
        channel_id: int,
        closed_by: int,
        reason: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        await self.conn.execute(
            """
            UPDATE tickets
            SET status = 'closed', closed_at = ?, closed_by = ?, close_reason = ?
            WHERE channel_id = ? AND status = 'open'
            """,
            (now, closed_by, reason, channel_id),
        )
        await self.conn.commit()
        return await self.get_ticket_by_channel(channel_id)

    async def get_open_tickets(self) -> list[dict[str, Any]]:
        async with self.conn.execute(
            "SELECT * FROM tickets WHERE status = 'open' ORDER BY created_at ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_stale_tickets(self, max_age_hours: int) -> list[dict[str, Any]]:
        cutoff = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(hours=max_age_hours)
        ).isoformat()
        # TODO: index (status, first_response_at, created_at) if table gets big
        # print(f"DEBUG: querying stale tickets with cutoff {cutoff}")
        async with self.conn.execute(
            """
            SELECT * FROM tickets
            WHERE status = 'open'
              AND created_at <= ?
              AND first_response_at IS NULL
            ORDER BY created_at ASC
            """,
            (cutoff,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
