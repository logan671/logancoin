# ProjectE-PolymarketTGtracker

## Quick Start (Server)
1) Create venv and install deps:
```
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2) Set env vars (example):
```
export PROJECTE_BOT_TOKEN="..."
export PROJECTE_CHANNEL_ID="-100xxxxxxxxxx"
export PROJECTE_RPC_URL="https://rpc.ankr.com/polygon/..."
export PROJECTE_POLL_SECONDS="10"
```

3) Start bot + tracker:
```
python3 bot.py
python3 tracker.py
```

## Files
- bot.py: Telegram bot command handler
- tracker.py: On-chain event polling + alerting
- db.py: SQLite storage
- market_cache.py: Gamma API token mapping
- config.py: Env config
