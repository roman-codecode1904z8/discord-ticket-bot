from prometheus_client import Counter, Gauge, Histogram, start_http_server
import logging

log = logging.getLogger(__name__)

TICKETS_CREATED = Counter(
    "ticketbot_tickets_created_total",
    "Total number of opened tickets",
    ["category"],
)

TICKETS_CLOSED = Counter(
    "ticketbot_tickets_closed_total",
    "Total number of closed tickets",
    ["category", "reason"],
)

TICKETS_OPEN = Gauge(
    "ticketbot_tickets_open",
    "Current number of open tickets",
    ["category"],
)

TICKETS_STALE = Gauge(
    "ticketbot_tickets_stale",
    "Number of open tickets without activity past stale threshold",
)

TICKET_RESOLUTION_SECONDS = Histogram(
    "ticketbot_ticket_resolution_seconds",
    "Time from ticket creation to close in seconds",
    ["category"],
    # 5m, 15m, 30m, 1h, 2h, 4h, 8h, 24h, 48h, 7d
    buckets=(300, 900, 1800, 3600, 7200, 14400, 28800, 86400, 172800, 604800),
)

DB_QUERY_SECONDS = Histogram(
    "ticketbot_db_query_duration_seconds",
    "SQLite query runtime",
    ["query_name"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)


def init_metrics(port: int = 9100, host: str = "0.0.0.0"):
    """Start Prometheus HTTP endpoint."""
    try:
        start_http_server(port, addr=host)
        log.info("Prometheus metrics listening on %s:%d", host, port)
    except OSError as e:
        log.error("failed to bind metrics server on %s:%d - %s", host, port, e)
        raise
