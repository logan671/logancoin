# PRD: 15min Polymarket Crypto Trading Bot

> **Version**: 1.0 (Final)
> **Last Updated**: 2026-02-12

## 1. Project Overview

| Item | Detail |
|------|--------|
| Project Name | 15min-poly-better |
| Folder | `ProjectG-15minpolybetter` |
| Goal | Polymarket 15분 크립토 마켓에서 모멘텀 기반 자동 매수/정산으로 수익 창출 |
| Starting Capital | $300 USDC (6 buy-ins × $50) |
| Deploy Server | 47.80.2.58 (Ubuntu 24.04, 4 vCPU, 7GB RAM) |
| Tech Stack | Python 3.11+ |
| Alert | Telegram Bot |

---

## 2. Core Strategy: Momentum-Based Tiered Entry

### Concept

바이낸스 실시간 가격 모멘텀을 감지하여, Polymarket 15분 Up/Down 마켓의 한쪽이
높은 확률(85%+)에 도달했을 때 매수. 정산 시 $1.00으로 수렴하여 차익 실현.

### Bankroll Structure (Poker-Style Buy-In)

| Item | Value |
|------|-------|
| Total Bankroll | $300 |
| Buy-in Size | $50 |
| Total Buy-ins | 6 |
| Active Buy-in | 1 at a time (test with $50 first) |

### Tiered Entry Table (per $50 buy-in)

| Zone | Odds Range | Signal Required | Bet Size (% of buy-in) | Bet Amount |
|------|-----------|-----------------|----------------------|------------|
| Caution | 85~89% | Strong Binance momentum (5min change >= 0.5%) | 5% | $2.50 |
| Standard | 90~94% | Binance momentum confirmed (5min change >= 0.3%) | 10% | $5.00 |
| Confidence | 95%+ | Minimal check (price direction match only) | 15% | $7.50 |

### Momentum Signal Definition

| Indicator | Threshold | Description |
|-----------|-----------|-------------|
| 5min price change | >= 0.3% (Standard), >= 0.5% (Caution) | Binance spot price change over last 5 minutes |
| Direction match | Required | Binance up → buy Up, Binance down → buy Down |
| Data freshness | < 3 seconds old | Stale data = no trade |

> **Note**: Volume spike was considered but excluded from v1.
> Rationale: Odds reaching 85%+ already implies market conviction. Adding volume
> filter reduces trading opportunities without proven benefit. May revisit after
> observation phase produces data.

### Liquidity Filter (NEW)

All conditions must pass before order submission:

| Filter | Minimum | Reason |
|--------|---------|--------|
| Best ask quantity | >= 3x bet size | Ensure order fills without slippage |
| Bid-ask spread | <= $0.02 | Tight spread = healthy market |
| Recent trade | Within last 5 minutes | Dead market = no entry |

If any filter fails → **skip this market, wait for next opportunity.**

### Entry Conditions (ALL must be true)

1. One side (Up or Down) odds >= 85%
2. Momentum signal passes (see table above)
3. Liquidity filter passes (see table above)
4. Remaining time in 15min window >= 2 minutes (avoid last-second chaos)
5. No existing open position on the same market (idempotency check)
6. Current buy-in balance >= minimum bet size for the zone
7. No active circuit breaker

### Exit Rules

- **No manual exit.** All positions are held until 15min market resolves.
- Market auto-settles to $1.00 (win) or $0.00 (lose).

---

## 3. Risk Management (Poker-Style Bankroll)

### Buy-In Lifecycle

```
$50 (start) ──┬── $75 (+50%) ──→ 승격: 2 buy-in 합산, 베팅 사이즈 유지
              ├── $100 (2x)  ──→ $50 회수 (원금 보호) + $50으로 계속
              └── $25 (-50%) ──→ 바인 버스트. 다음 buy-in 투입
```

### Buy-In Management

| Condition | Action |
|-----------|--------|
| Buy-in hits $75 (+50%) | Merge with next buy-in, keep bet sizes |
| Buy-in hits $100 (2x) | Withdraw $50 (protect capital), continue with $50 |
| Buy-in hits $25 (-50%) | **Buy-in bust.** Deploy next buy-in. |
| 3 consecutive buy-in busts | **Full stop.** Strategy review required. |
| All 6 buy-ins busted | **Total stop.** $300 lost. Walk away. |

### Within Buy-In Circuit Breakers

| Trigger | Action |
|---------|--------|
| 3 consecutive losses | Pause 1 hour |
| Daily loss >= 30% of active buy-in | Stop trading for the day |
| Active buy-in < $25 | **Buy-in bust.** Switch to next. |

### Position Limits

| Active Buy-In | Max Single Bet | Max Concurrent Bets |
|---------------|---------------|---------------------|
| $50 | $7.50 (15%) | 2 |
| $75+ | $11.25 (15%) | 2 |
| < $30 | $3.00 (10%) | 1 |

### Abnormal Event Handling (NEW)

| Event | Detection | Action |
|-------|-----------|--------|
| Binance WebSocket disconnect | No data for > 5s | **Halt new entries.** Keep existing positions. |
| Polymarket API error | HTTP 5xx or timeout | **Halt new entries.** Retry with backoff. |
| Price data mismatch | Binance/Polymarket direction conflict > 30s | **Halt new entries.** Log for review. |
| Oracle delay | Market not resolving after expected time | Do nothing. Wait for resolution. |
| Sudden odds flip | 85%+ drops below 70% within 60s | Log as anomaly. No action (position already held). |
| Server resource issue | CPU > 90% or memory > 85% | **Halt new entries.** Alert via Telegram. |

---

## 4. Expected P&L Model ($50 buy-in, 2% edge)

### Per Trade by Zone

| Zone | Bet | Win | Loss | EV (2% edge) |
|------|-----|-----|------|-------------|
| 85~89% ($2.50) | $2.50 | +$0.35 | -$2.52 | +$0.012 |
| 90~94% ($5.00) | $5.00 | +$0.53 | -$5.03 | +$0.086 |
| 95%+ ($7.50) | $7.50 | +$0.37 | -$7.52 | +$0.136 |

### Single Buy-In Projection ($50, conservative)

| Metric | Value |
|--------|-------|
| Trades per day | ~10 |
| Avg bet (mixed zones) | ~$4.50 |
| EV per trade | ~+$0.07 |
| Daily expected profit | ~+$0.70 |
| Days to +50% ($75) | ~36 days |
| Days to 2x ($100) | ~71 days |
| Buy-in bust probability | ~30% (per buy-in) |

### Full Bankroll Projection ($300 = 6 buy-ins)

| Scenario | Probability | Outcome |
|----------|-------------|---------|
| 1st buy-in survives to $100 | ~40% | +$50 profit, continue with house money |
| Bust 1, survive on 2nd | ~25% | -$50 → eventually recover |
| Bust 2, survive on 3rd | ~15% | -$100 → slow grind back |
| Bust 3+ (strategy fails) | ~20% | **Stop. Review. Retool.** |

> **Disclaimer**: 2% edge is an ASSUMPTION. Must be validated in Phase 0 (observation mode)
> before risking real capital. If observation shows Net EV <= 0, strategy must be revised.

---

## 5. Technical Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Main Bot (Python)                      │
├──────────────┬──────────────┬────────────────────────────┤
│  Price Feed  │ Trade Engine │  Risk Manager              │
│  (Binance    │ (Polymarket  │  (Position sizing,         │
│   WebSocket) │  CLOB SDK)   │   circuit breakers,        │
│              │              │   abnormal event handler)  │
├──────────────┴──────────────┴────────────────────────────┤
│                   Signal Engine                           │
│  (Momentum calc + Liquidity filter + Entry conditions)    │
├──────────────────────────────────────────────────────────┤
│                   Market Scanner                          │
│  (Gamma API: discover active 15min markets)               │
├──────────────────────────────────────────────────────────┤
│           Order State Machine (NEW)                       │
│  IDLE → SIGNAL → CHECK_LIQUIDITY → SUBMIT → PENDING →    │
│  FILLED / REJECTED → AWAITING_SETTLE → SETTLED            │
├──────────────────────────────────────────────────────────┤
│               State & Logging (SQLite)                    │
├──────────────────────────────────────────────────────────┤
│              Telegram Alert Bot                           │
└──────────────────────────────────────────────────────────┘
```

### Order State Machine (NEW)

```
IDLE ──(signal detected)──→ SIGNAL_DETECTED
  │
  ├──(liquidity check fail)──→ SKIPPED (log reason, return to IDLE)
  │
  └──(liquidity check pass)──→ SUBMITTING
                                  │
                    ├──(API error)──→ SUBMIT_FAILED (log, return to IDLE)
                    │
                    └──(order accepted)──→ PENDING
                                            │
                              ├──(filled)──→ POSITION_OPEN
                              │                   │
                              │         (market resolves)──→ SETTLED (record P&L)
                              │
                              └──(rejected/expired)──→ ORDER_FAILED (log, return to IDLE)
```

- Each order has a unique `order_id` (UUID) for idempotency
- Only ONE active order per market at a time
- State transitions are logged to SQLite with timestamps

### Module Breakdown

| Module | Responsibility | Key Libraries |
|--------|---------------|---------------|
| `market_scanner.py` | 15분 마켓 디스커버리, 슬러그 생성, 토큰 ID 조회 | `requests` |
| `price_feed.py` | Binance BTC/ETH 실시간 가격 수신 | `websockets` |
| `odds_feed.py` | Polymarket 실시간 오즈/오더북 수신 | `websockets`, `py-clob-client` |
| `signal_engine.py` | 모멘텀 계산 + 유동성 필터 + 진입 조건 판단 | custom logic |
| `trade_executor.py` | 주문 상태 머신, 주문 생성/관리 (FOK market order) | `py-clob-client` |
| `risk_manager.py` | 포지션 사이즈, 서킷브레이커, 뱅크롤 관리, 이상 이벤트 처리 | custom logic |
| `state_store.py` | 거래 기록, 뱅크롤 추적, 성과 분석, 주문 상태 로깅 | `sqlite3` |
| `telegram_bot.py` | 매수/정산/일일요약/이상 이벤트 알림 전송 | `python-telegram-bot` |
| `main.py` | Orchestrator: 모든 모듈 연결, 메인 루프 | `asyncio` |
| `config.py` | 설정값 (API keys, thresholds, bet sizes) | `pydantic` |
| `observer.py` | Phase 0 관찰 모드: 시그널 기록만 하고 실제 매수 안 함 | `sqlite3` |
| `replay_sim.py` | 관찰 데이터 기반 간이 시뮬레이션 (리플레이 백테스트) | `pandas` |

---

## 6. API Integration Details

### Polymarket

| API | Purpose | Auth |
|-----|---------|------|
| Gamma API (`gamma-api.polymarket.com`) | Market discovery (slug → token IDs) | None |
| CLOB REST (`clob.polymarket.com`) | Order placement, balance check | L2 (HMAC) |
| CLOB WebSocket (`wss://ws-subscriptions-clob.polymarket.com`) | Real-time odds/orderbook | None |
| RTDS WebSocket (`wss://ws-live-data.polymarket.com`) | Crypto price feed (Chainlink) | None |

### Binance

| API | Purpose |
|-----|---------|
| WebSocket (`wss://stream.binance.com:9443/ws`) | Real-time BTC/ETH price |
| Streams: `btcusdt@trade`, `ethusdt@trade` | Individual trade data |

### Telegram

| API | Purpose |
|-----|---------|
| Bot API (`api.telegram.org/bot{TOKEN}`) | Send alerts to user's chat |

---

## 7. Wallet & Authentication Setup

### Requirements

| Item | Detail |
|------|--------|
| Polygon Wallet | New EOA wallet (MetaMask or generated via ethers.js) |
| USDC Balance | $300 USDCe on Polygon network |
| Polymarket Approval | USDC allowance to CTF Exchange contract |
| API Credentials | Derived from wallet private key via EIP-712 |

### Security

- Private key stored in `.env` file (NOT in code)
- `.env` added to `.gitignore`
- Server access via SSH only
- Wallet is single-purpose (trading only, no other assets)

---

## 8. Telegram Alert Messages

### Trade Executed
```
🟢 BUY: BTC Up (15min)
Odds: 91.5% | Bet: $5.00 | Zone: Standard
Market closes: 14:45 UTC
Buy-in: $47.30 (remaining)
```

### Trade Settled
```
✅ WIN: BTC Up (15min) → $1.00
Profit: +$0.53 (net of fees)
Buy-in: $52.83 | Win streak: 4
```

```
❌ LOSS: ETH Down (15min) → $0.00
Loss: -$5.03
Buy-in: $42.27 | ⚠️ 2 consecutive losses
```

### Daily Summary
```
📊 Daily Summary (2026-02-12)
Trades: 12 (10W / 2L)
P&L: +$1.26
Buy-in: $51.26 (+2.5%) | Total bankroll: $301.26
Best: BTC Up +$0.53
Worst: ETH Down -$5.03
```

### Circuit Breaker
```
🛑 CIRCUIT BREAKER ACTIVATED
Reason: 3 consecutive losses
Action: Paused for 1 hour
Resume: 15:30 UTC
```

### Abnormal Event (NEW)
```
⚠️ ABNORMAL EVENT
Type: Binance WebSocket disconnected
Action: New entries halted
Existing positions: 1 (BTC Up, awaiting settlement)
Status: Reconnecting...
```

### Observation Mode Report (NEW)
```
👁️ Phase 0 Observation Report (2026-02-12)
Signals detected: 18
Would-have-traded: 12 (passed all filters)
Simulated results: 10W / 2L (83.3%)
Simulated EV: +$0.04/trade
Net EV status: ✅ POSITIVE (proceed to Phase 1)
```

---

## 9. Deployment Plan

| Phase | Task | Duration | Success Gate |
|-------|------|----------|-------------|
| Phase 0 (NEW) | **Observation mode**: collect signals, simulate trades, validate edge | Day 1-7 | Net EV > 0 over 100+ signals |
| Phase 1 | Core modules (scanner, feeds, signal engine, observer) | Day 1-3 | All feeds connected, signals logging |
| Phase 2 | Trade executor + risk manager + order state machine | Day 4-6 | Dry-run orders pass validation |
| Phase 3 | Telegram bot + state store | Day 7 | Alerts delivered < 5s |
| Phase 4 | Paper trading (full pipeline, no real money) | Day 8-14 | 50+ paper trades, win rate >= 88% at 90%+ zone |
| Phase 5 | Micro live ($2.50 bets, 1st buy-in) | Day 15-21 | Net EV positive over 50+ real trades |
| Phase 6 | Full buy-in ($50) deployment | Day 22+ | Sustained positive performance |

> **Phase 0 runs concurrently with Phase 1-3.**
> Build the bot AND collect observation data at the same time.
> By the time the bot is ready for paper trading, we already have edge validation data.

### Server Setup

```
Server: 47.80.2.58
OS: Ubuntu 24.04
Runtime: Python 3.11 + venv
Process Manager: systemd service
Logging: journalctl + SQLite
Auto-restart: on failure
```

---

## 10. Success Criteria

| Metric | Target | Measurement | Phase |
|--------|--------|-------------|-------|
| Observation Net EV | > 0 per trade | 100+ simulated signals | Phase 0 |
| Paper trade win rate | >= 88% (at 90%+ zone) | 50+ trades | Phase 4 |
| Real trade Net EV | > 0 after fees | 50+ live trades | Phase 5 |
| Monthly ROI | >= 10% per buy-in | After fees | Phase 6 |
| Max drawdown | < 50% of active buy-in | Per session | All |
| Uptime | >= 99% | systemd monitoring | Phase 4+ |
| Alert latency | < 5 seconds | Telegram delivery | Phase 3+ |

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **No real edge exists** | Strategy unprofitable | Phase 0 observation validates before real money |
| **Low liquidity at 90%+** | Orders don't fill / slippage | Liquidity filter (3x bet size, $0.02 spread) |
| Polymarket API downtime | Missed trades | Halt new entries + retry with backoff |
| Binance WebSocket disconnect | Bad signals | Auto-reconnect + stale data check (> 3s = halt) |
| Strategy edge disappears | Losses | Circuit breaker + weekly performance review |
| Wallet compromise | Total loss | Separate trading wallet, only $50 active |
| Fee structure changes | Margin shrink | Monitor Polymarket announcements |
| Server crash | Missed trades | systemd auto-restart + health check |
| Duplicate orders | Double exposure | Order state machine + idempotency key per market |
| Last-minute market flip | Unexpected loss | 2min buffer rule + log anomalies for pattern analysis |

---

## 12. Open Questions (Resolved)

| Question | Resolution |
|----------|-----------|
| Momentum criteria definition? | 5min price change >= 0.3% (Standard) / >= 0.5% (Caution). Direction match required. |
| Liquidity criteria? | Ask qty >= 3x bet, spread <= $0.02, recent trade within 5min. |
| Order fill failure handling? | Order state machine: REJECTED → log → return to IDLE. No retry on same market window. |
| Abnormal event handling? | Halt new entries, keep existing positions, alert via Telegram, auto-recover when resolved. |
| Volume as signal? | Excluded from v1. May revisit after observation data analysis. |
| Backtest in scope? | Yes. `replay_sim.py` uses Phase 0 observation data for replay-based simulation. |

---

## 13. Out of Scope (v1)

- Multi-market arbitrage (buy both sides)
- SOL/XRP markets (start with BTC/ETH only for liquidity)
- Web dashboard (Telegram alerts are sufficient for v1)
- Volume-based signal filtering
- Automated bankroll withdrawal
- API key rotation policy (sufficient for $50 test scale)
