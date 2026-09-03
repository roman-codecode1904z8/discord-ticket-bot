import pytest
import aiosqlite
import time
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

    active = await db.get_active_ticket_for_user(user_id=300, guild_id=100)
    assert active is None

    by_chan = await db.get_ticket_by_channel(200)
    assert by_chan is None


@pytest.mark.asyncio
async def test_stale_tickets_query(temp_db):
    # create two tickets, backdate one by 3600s
    t1 = await db.create_ticket(guild_id=1, channel_id=10, user_id=100, user_name="old_user")
    t2 = await db.create_ticket(guild_id=1, channel_id=20, user_id=200, user_name="new_user")

    two_hours_ago = time.time() - 7200
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute(
            "UPDATE tickets SET last_activity_at = ? WHERE id = ?",
            (two_hours_ago, t1),
        )
        await conn.commit()

    stale = await db.get_stale_tickets(stale_threshold_seconds=3600)
    stale_ids = [row["id"] for row in stale]
    assert t1 in stale_ids
    assert t2 not in stale_ids


@pytest.mark.asyncio
async def test_touch_ticket_activity(temp_db):
    tid = await db.create_ticket(guild_id=1, channel_id=11, user_id=101, user_name="touch_test")
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute("UPDATE tickets SET last_activity_at = 1000 WHERE id = ?", (tid,))
        await conn.commit()

    await db.touch_ticket_activity(channel_id=11)

    async with aiosqlite.connect(db.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT last_activity_at FROM tickets WHERE id = ?", (tid,)) as cur:
            row = await cur.fetchone()
            assert row["last_activity_at"] > 1000
