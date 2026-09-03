import pytest
import aiosqlite
from ticketbot import db


@pytest.fixture
async def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_tickets.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))
    await db.init_db()
    return db_path


@pytest.mark.asyncio
async def test_create_and_get_ticket(temp_db):
    tid = await db.create_ticket(
        guild_id=123,
        channel_id=456,
        user_id=789,
        user_name="alice#0001",
    )
    assert tid == 1

    active = await db.get_active_ticket_for_user(user_id=789, guild_id=123)
    assert active is not None
    assert active["id"] == 1
    assert active["user_name"] == "alice#0001"
    assert active["status"] == "open"


@pytest.mark.asyncio
async def test_close_ticket(temp_db):
    tid = await db.create_ticket(
        guild_id=100,
        channel_id=200,
        user_id=300,
        user_name="bob#0002",
    )
    duration = await db.close_ticket(tid, closed_by_id=999)
    assert duration is not None
    assert duration >= 0

    # once closed, active lookup should return None
    active = await db.get_active_ticket_for_user(user_id=300, guild_id=100)
    assert active is None

    by_chan = await db.get_ticket_by_channel(200)
    assert by_chan is None
