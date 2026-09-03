import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    token: str
    guild_id: int
    category_id: int
    support_role_id: int
    alert_channel_id: int
    db_path: Path
    metrics_port: int
    stale_hours: int


def load_config() -> Config:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN is required")

    guild_id = int(os.getenv("GUILD_ID", "0"))
    if not guild_id:
        raise ValueError("GUILD_ID is required and must be non-zero")

    category_id = int(os.getenv("TICKET_CATEGORY_ID", "0"))
    support_role_id = int(os.getenv("SUPPORT_ROLE_ID", "0"))
    alert_channel_id = int(os.getenv("ALERT_CHANNEL_ID", "0"))
    db_path = Path(os.getenv("DB_PATH", "tickets.db"))
    metrics_port = int(os.getenv("PROMETHEUS_PORT", "9100"))
    stale_hours = int(os.getenv("STALE_THRESHOLD_HOURS", "24"))

    return Config(
        token=token,
        guild_id=guild_id,
        category_id=category_id,
        support_role_id=support_role_id,
        alert_channel_id=alert_channel_id,
        db_path=db_path,
        metrics_port=metrics_port,
        stale_hours=stale_hours,
    )
