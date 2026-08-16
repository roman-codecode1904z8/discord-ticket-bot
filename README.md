# ticketbot

Small discord bot we use for internal tech support tickets. Keeps everything in SQLite and exports Prometheus metrics for resolution time and open queues.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Copy `.env.example` to `.env` and fill in your details:

```env
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=123456789012345678
TICKETS_CATEGORY_ID=123456789012345678
SUPPORT_ROLE_ID=123456789012345678
METRICS_PORT=9100
DATABASE_PATH=tickets.db
STALE_HOURS=24
```

## Running

```bash
python -m ticketbot
```
