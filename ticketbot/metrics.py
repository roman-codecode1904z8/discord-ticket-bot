from prometheus_client import Counter, Gauge, start_http_server
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


def init_metrics(port: int = 9100, host: str = "0.0.0.0"):
    """Start Prometheus HTTP endpoint."""
    try:
        start_http_server(port, addr=host)
        log.info("Prometheus metrics listening on %s:%d", host, port)
    except OSError as e:
        log.error("failed to bind metrics server on %s:%d - %s", host, port, e)
        raise
