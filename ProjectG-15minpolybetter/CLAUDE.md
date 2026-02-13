# ProjectG - 15min Polymarket Trading Bot

## Overview
Polymarket 15분 크립토(BTC/ETH) Up/Down 마켓에서 모멘텀 기반 자동 매수 봇.

## Tech Stack
- Python 3.11+
- asyncio (main event loop)
- websockets (Binance, Polymarket feeds)
- py-clob-client (Polymarket CLOB SDK)
- pydantic (config)
- SQLite (state/logging)

## Project Structure
```
src/           # source code
tests/         # unit tests
data/          # SQLite DB, logs (gitignored)
```

## Rules
- Code comments in English
- No hardcoded secrets - use .env
- All async code uses asyncio
- State transitions logged to SQLite
