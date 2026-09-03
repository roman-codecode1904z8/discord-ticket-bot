import pytest
from prometheus_client import REGISTRY
from ticketbot import metrics


def test_ticket_created_counter():
    before = REGISTRY.get_sample_value("tickets_created_total", {"guild_id": "999"}) or 0.0
    metrics.record_ticket_created(guild_id="999")
    after = REGISTRY.get_sample_value("tickets_created_total", {"guild_id": "999"})
    assert after == before + 1.0


def test_ticket_resolved_histogram():
    metrics.record_ticket_resolved(guild_id="999", duration_seconds=42.5)
    count = REGISTRY.get_sample_value("ticket_resolution_seconds_count", {"guild_id": "999"})
    assert count is not None
    assert count >= 1.0


def test_stale_ticket_gauge():
    metrics.set_stale_ticket_count(guild_id="999", count=4)
    val = REGISTRY.get_sample_value("stale_tickets_current", {"guild_id": "999"})
    assert val == 4.0

    metrics.set_stale_ticket_count(guild_id="999", count=0)
    val = REGISTRY.get_sample_value("stale_tickets_current", {"guild_id": "999"})
    assert val == 0.0
