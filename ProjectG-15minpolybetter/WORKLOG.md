# ProjectG Worklog

## 2026-02-13 (Codex + User)

### Goal for this session
- Continue ProjectG implementation with three concrete tracks:
- Implement `odds_feed.py`
- Implement `signal_engine.py`
- Add `market_scanner` integration test path

### What was implemented
- Added `src/market_scanner.py`
- 15-minute UTC slug generation (`get_current_slug`)
- Gamma market response parser (`parse_market_from_gamma`)
- Async market fetch by slug (`fetch_market_by_slug`)

- Added `src/price_feed.py`
- 5-minute price buffer using deque
- 5-minute momentum calculation (`get_5min_change`)
- freshness check (`is_fresh`)
- direction inference (`get_direction`)

- Added `src/odds_feed.py`
- Orderbook top-level parser (`parse_orderbook_message`)
- Liquidity validation (`passes_liquidity_filter`)
- Checks: spread, ask depth multiplier, recent trade freshness

- Added `src/signal_engine.py`
- Zone classification (`caution`, `standard`, `confidence`)
- Bet sizing calculation
- Entry decision function (`should_trade`) with reason codes
- Refactored to avoid hard dependency on `config.py` during unit tests

### Tests added
- `tests/test_market_scanner.py`
- `tests/test_price_feed.py`
- `tests/test_odds_feed.py`
- `tests/test_signal_engine.py`
- `tests/test_market_scanner_integration.py`
  - Live API test is opt-in only:
  - `RUN_LIVE_API_TESTS=1` required
  - skipped by default for local/CI stability

### Validation result
- Command: `python3 -m unittest discover -s tests`
- Result: `Ran 16 tests, OK (skipped=1)`

### Important context for next machine/user
- Current work is foundation for Phase 1~2:
- market discovery
- momentum feed utilities
- liquidity filter
- initial decision engine
- Not yet implemented:
- real websocket clients for Binance/Polymarket
- order execution state machine
- SQLite persistence pipeline
