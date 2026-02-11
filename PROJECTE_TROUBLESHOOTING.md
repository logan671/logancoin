# ProjectE Troubleshooting Log

Updated: 2026-02-10

## Summary
This document records major issues encountered while building the Polymarket Telegram tracker (ProjectE), the root causes, and fixes applied.

## Key Issues & Fixes

1) **Tracker not alerting after reboot**
- Symptom: No alerts; log showed `Block range is too large`.
- Cause: RPC limits on `eth_getLogs` block range.
- Fix: Query logs in smaller ranges + lag jump logic.
  - Added `MAX_BLOCK_RANGE` chunking.
  - Added `MAX_LAG_BLOCKS` auto-jump to latest when behind.

2) **Tracker errors from web3 decode**
- Symptom: `decode_abi` missing in web3 v6.
- Cause: Deprecated API.
- Fix: Use `eth_abi.decode`.

3) **Duplicate alerts per transaction**
- Symptom: Same tx produced two messages.
- Cause: Multiple OrderFilled logs per tx; both matched watched wallet.
- Fix: Only emit one alert per `(tx_hash, address)` and select the log with larger USDC amount.

4) **Wrong side/Yes-No direction**
- Symptom: “Yes bought” shown as “No sold”.
- Cause: Multiple OrderFilled logs; wrong log chosen.
- Fix: Same as #3 (choose log with larger USDC amount).

5) **Market title missing (종목: -)**
- Symptom: Title not shown even though token exists.
- Causes:
  - Gamma API intermittently failing (DNS/SSL/timeouts).
  - `outcomes`/`clobTokenIds` returned as JSON strings instead of arrays.
- Fixes:
  - Added retry + backoff + logging for Gamma API.
  - Parse `outcomes`/`clobTokenIds` when they are JSON strings.
  - Skip token_id=0 (USDC) lookups.
  - If token match fails, still return market question/slug.

6) **Cache warm-up too slow**
- Symptom: Full market cache took minutes; blocked alerts.
- Fix:
  - Fast lookup by token using `clob_token_ids`.
  - Background cache warmer timer.

7) **Dome WebSocket test**
- Symptom: WS ack succeeded but no events.
- Likely cause: Plan/permissions or user filter not emitting events.
- Status: Disabled for now; on-chain tracking is primary.

8) **Server instability / SSH timeouts**
- Symptom: SSH intermittent timeouts.
- Findings: No OOM logs; uptime stable at times; likely networking/IP changes or brief disconnects.
- Mitigation:
  - Suggested automatic recovery and external uptime monitoring.

## Current Behavior (as of 2026-02-10)
- On-chain alerts are working.
- Message format includes:
  - Wallet alias/note/address
  - Market title
  - Direction sentence with estimated shares and total USDC
  - Polymarket market link
  - Profile link
  - Polygonscan tx link
- Low-value trades (< $100) are filtered except for the whitelisted wallet:
  - 0x811192618fb0c7fcc678a81bb7c796a554bcb832

## Server Services
- projecte-tracker.service
- projecte-bot.service
- projecte-cachewarm.timer (hourly)

## Logs
- Tracker: /home/ecs-user/ProjectE-PolymarketTGtracker/logs/tracker.log
- Market cache: /home/ecs-user/ProjectE-PolymarketTGtracker/market_cache.log

## Files
- tracker.py
- market_cache.py
- config.py


## Latest Updates (2026-02-10)

- Message format revamped (separators, links, wallet label with alias/note/address).
- Polymarket market title parsing fixed (Gamma `outcomes`/`clobTokenIds` can be JSON strings).
- Share count now estimated via `USDC / price` for closer UI match.
- Duplicate tx link removed.
- Filter added: skip trades below $100 (except whitelisted wallet).
- Added daily per-market cap: 3+ trades per wallet/market/day are skipped.
- Added track button + /tracking list:
  - Inline button now uses short token (64B limit workaround).
  - Tracking stored in DB; /tracking shows linked list.
- Added “exit before resolution” warning when tracked wallet flips direction on same market.

Files touched:
- tracker.py
- market_cache.py
- bot.py
- db.py
- CLAUDE.md (command explanation exceptions)
