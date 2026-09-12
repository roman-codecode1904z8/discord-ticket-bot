# ticketbot

Small discord bot we use for internal tech support tickets. Keeps everything in SQLite and exports Prometheus metrics for resolution time and open queues.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[fast]"
```

Copy `.env.example` to `.env` and fill in your details:

```env
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=123456789012345678
TICKETS_CATEGORY_ID=123456789012345678
SUPPORT_ROLE_ID=123456789012345678
METRICS_PORT=9100
DATABASE_PATH=data/tickets.db
STALE_HOURS=24
CHECK_INTERVAL_SECONDS=300
```

## Running

```bash
python -m ticketbot
```

## Metrics

Scrape `http://localhost:9100/metrics`. Exported gauges and histograms:

- `ticketbot_open_tickets_count`: Current open ticket count.
- `ticketbot_stale_tickets_count`: Tickets with no staff reply for longer than `STALE_HOURS`.
- `ticketbot_resolution_duration_seconds`: Histogram of time elapsed from ticket creation to close.
- `ticketbot_first_response_seconds`: Histogram of time between ticket creation and first staff message.

<!-- checked: 2026-09-12 -->
