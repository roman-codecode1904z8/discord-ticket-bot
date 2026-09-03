import logging
import asyncio
import discord
from ticketbot import db, metrics

log = logging.getLogger(__name__)


class CreateTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # TODO: add dropdown for ticket category (billing/tech/general) once server adds roles
    @discord.ui.button(
        label="Open Ticket",
        style=discord.ButtonStyle.primary,
        emoji="📩",
        custom_id="ticketbot:create_ticket",
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Tickets can only be created in a server.", ephemeral=True)
            return

        existing = await db.get_active_ticket_for_user(interaction.user.id, guild.id)
        if existing:
            await interaction.response.send_message(
                f"You already have an open ticket in <#{existing['channel_id']}>.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        category = discord.utils.get(guild.categories, name="tickets")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

        channel_name = f"ticket-{interaction.user.name.lower()[:15]}"
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket for {interaction.user.display_name} (ID: {interaction.user.id})",
            )
        except discord.Forbidden:
            log.error("missing permissions to create ticket channel in guild %s", guild.id)
            await interaction.followup.send("Bot lacks permission to create channels.", ephemeral=True)
            return

        ticket_id = await db.create_ticket(
            guild_id=guild.id,
            channel_id=channel.id,
            user_id=interaction.user.id,
            user_name=str(interaction.user),
        )

        metrics.record_ticket_created(guild_id=str(guild.id))

        embed = discord.Embed(
            title=f"Ticket #{ticket_id}",
            description=f"Welcome {interaction.user.mention}! Support staff will be with you shortly.\nClick below when the issue is resolved.",
            color=0x2B2D31,
        )
        await channel.send(embed=embed, view=TicketControlView())
        await interaction.followup.send(f"Ticket opened: {channel.mention}", ephemeral=True)


class ConfirmCloseView(discord.ui.View):
    def __init__(self, ticket_id: int):
        super().__init__(timeout=30)
        self.ticket_id = ticket_id

    @discord.ui.button(label="Yes, close it", style=discord.ButtonStyle.danger, custom_id="ticketbot:confirm_close")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        await interaction.response.edit_message(view=self)

        duration_sec = await db.close_ticket(self.ticket_id, closed_by_id=interaction.user.id)
        if duration_sec is not None and interaction.guild_id:
            metrics.record_ticket_resolved(guild_id=str(interaction.guild_id), duration_seconds=duration_sec)

        await interaction.followup.send("Ticket closed. Deleting channel in 3 seconds...")
        await asyncio.sleep(3)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except discord.HTTPException as e:
            log.warning("failed to delete channel %s: %s", interaction.channel_id, e)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="ticketbot:cancel_close")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Ticket closure cancelled.", view=None)


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticketbot:close_ticket",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await db.get_ticket_by_channel(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message("This channel is not an active ticket.", ephemeral=True)
            return

        # print(f"DEBUG: close prompt shown for ticket {ticket['id']}")
        view = ConfirmCloseView(ticket["id"])
        await interaction.response.send_message("Are you sure you want to close this ticket?", view=view, ephemeral=True)
