# WBS (Work Breakdown Structure)

> **Project**: 15min-poly-better
> **Created**: 2026-02-12
> **Total Phases**: 6 (Phase 0~5 concurrent, Phase 6 after validation)

---

## Phase 0: Project Setup

> 프로젝트 뼈대를 세우고, 개발 환경을 준비한다.

- [ ] **0-1. 프로젝트 폴더 구조 생성**
  - [ ] `src/` 폴더 (소스코드)
  - [ ] `tests/` 폴더 (테스트)
  - [ ] `data/` 폴더 (SQLite DB, 로그)
  - [ ] `.env.example` (환경변수 템플릿)
  - [ ] `.gitignore` (.env, data/, __pycache__ 등)
  - [ ] `requirements.txt` (의존성 목록)
  - [ ] `CLAUDE.md` (프로젝트별 규칙)

- [ ] **0-2. Python 가상환경 + 의존성 설치**
  - [ ] `python -m venv venv`
  - [ ] `pip install py-clob-client websockets python-telegram-bot pydantic pandas aiohttp`
  - [ ] `pip freeze > requirements.txt`

- [ ] **0-3. config.py 작성**
  - [ ] pydantic BaseSettings 기반 설정 클래스
  - [ ] `.env`에서 읽어올 항목: `PRIVATE_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
  - [ ] 전략 상수: 오즈 임계값, 베팅 비율, 모멘텀 기준값
  - [ ] 뱅크롤 상수: buy-in 크기, bust 기준, circuit breaker 값

---

## Phase 1: Data Feeds (Day 1~2)

> 실시간 데이터를 받아오는 파이프라인을 만든다.
> Phase 0(관찰 모드)도 여기서 시작.

### Step 1-1: Market Scanner

- [ ] **1-1a. 슬러그 생성 함수**
  - [ ] `get_current_slug(coin, timeframe)` → `btc-updown-15m-{timestamp}`
  - [ ] UTC 기준 15분 단위 floor 계산
  - [ ] BTC, ETH 두 코인 지원

- [ ] **1-1b. Gamma API로 마켓 조회**
  - [ ] slug → condition_id, clob_token_ids (Yes/No) 조회
  - [ ] 마켓 상태 확인 (active/closed/resolved)
  - [ ] 15분마다 새 마켓 자동 갱신

- [ ] **1-1c. 마켓 스캐너 테스트**
  - [ ] 현재 활성 BTC/ETH 15분 마켓 조회 성공 확인
  - [ ] 마켓 전환(15분 경과) 시 자동 갱신 확인

### Step 1-2: Binance Price Feed

- [ ] **1-2a. WebSocket 연결**
  - [ ] `wss://stream.binance.com:9443/ws/btcusdt@trade` 연결
  - [ ] `wss://stream.binance.com:9443/ws/ethusdt@trade` 연결
  - [ ] auto-reconnect 로직 (연결 끊김 시 5초 후 재접속)

- [ ] **1-2b. 5분 가격 버퍼 구현**
  - [ ] 최근 5분간 가격 데이터 deque로 저장
  - [ ] `get_5min_change()` → 5분 전 대비 변화율(%) 계산
  - [ ] 데이터 신선도 체크: 마지막 데이터가 3초 이내인지

- [ ] **1-2c. Price Feed 테스트**
  - [ ] 실시간 BTC/ETH 가격 수신 확인
  - [ ] 5분 변화율 계산 정확성 확인
  - [ ] 재접속 로직 동작 확인

### Step 1-3: Polymarket Odds Feed

- [ ] **1-3a. CLOB WebSocket 연결**
  - [ ] `wss://ws-subscriptions-clob.polymarket.com/ws/market` 연결
  - [ ] 현재 활성 마켓의 token_id로 구독
  - [ ] auto-reconnect 로직

- [ ] **1-3b. 오즈/오더북 파싱**
  - [ ] 실시간 best bid/ask 추출
  - [ ] Up/Down 각 오즈(확률) 계산
  - [ ] 오더북 depth (호가 잔량) 파싱

- [ ] **1-3c. Odds Feed 테스트**
  - [ ] 실시간 BTC Up/Down 오즈 수신 확인
  - [ ] 오더북 depth 데이터 정상 수신 확인
  - [ ] 마켓 전환 시 새 토큰으로 재구독 확인

### Step 1-4: Observer (Phase 0 관찰 모드)

- [ ] **1-4a. 시그널 로깅 구현**
  - [ ] SQLite 테이블: `observations` (timestamp, coin, odds, binance_price, momentum, would_trade, actual_result)
  - [ ] 시그널 발생 시 기록 (매수 안 함, 기록만)
  - [ ] 마켓 정산 후 실제 결과 업데이트

- [ ] **1-4b. 관찰 리포트 생성**
  - [ ] 일일 관찰 요약: 시그널 수, 가상 승률, 가상 EV
  - [ ] 텔레그램으로 관찰 리포트 전송

---

## Phase 2: Signal Engine + Trade Executor (Day 3~5)

> 시그널 판단 + 실제 주문 실행 로직을 만든다.

### Step 2-1: Signal Engine

- [ ] **2-1a. 모멘텀 시그널 계산**
  - [ ] 바이낸스 5분 변화율 >= 0.3% (Standard) / >= 0.5% (Caution)
  - [ ] 방향 일치 확인: 바이낸스 상승 + Up 85%+ / 하락 + Down 85%+
  - [ ] 데이터 신선도 체크 (3초 이내)

- [ ] **2-1b. 유동성 필터**
  - [ ] best ask 잔량 >= 베팅의 3배
  - [ ] bid-ask 스프레드 <= $0.02
  - [ ] 최근 5분 내 체결 기록 존재

- [ ] **2-1c. 진입 조건 통합 판단**
  - [ ] `should_trade()` 함수: 모든 조건 AND 체크
  - [ ] zone 판별 (Caution / Standard / Confidence)
  - [ ] 베팅 사이즈 계산 (buy-in 잔액 기반)

- [ ] **2-1d. Signal Engine 테스트**
  - [ ] 각 조건별 True/False 케이스 유닛 테스트
  - [ ] 유동성 부족 시 SKIP 동작 확인
  - [ ] zone별 베팅 사이즈 계산 정확성 확인

### Step 2-2: Trade Executor (Order State Machine)

- [ ] **2-2a. 주문 상태 머신 구현**
  - [ ] 상태: IDLE → SIGNAL → CHECK_LIQUIDITY → SUBMIT → PENDING → FILLED → SETTLED
  - [ ] 에러 상태: SKIPPED, SUBMIT_FAILED, ORDER_FAILED
  - [ ] 상태 전이 로깅 (SQLite)

- [ ] **2-2b. Polymarket 주문 실행**
  - [ ] py-clob-client 초기화 (L2 인증)
  - [ ] FOK (Fill-Or-Kill) 마켓 오더 생성
  - [ ] 주문 결과 확인 (체결/거절)
  - [ ] idempotency: 마켓당 1개 주문만 허용

- [ ] **2-2c. 정산 결과 수집**
  - [ ] 마켓 resolved 이벤트 감지
  - [ ] 승/패 판정 + 실제 수익/손실 계산
  - [ ] SQLite에 거래 기록 저장

- [ ] **2-2d. Trade Executor 테스트 (dry-run)**
  - [ ] 주문 생성 → 상태 전이 로그 확인
  - [ ] 체결 실패 시 IDLE 복귀 확인
  - [ ] 중복 주문 방지 확인

---

## Phase 3: Risk Manager (Day 5~6)

> 뱅크롤 관리 + 안전장치를 만든다.

### Step 3-1: Bankroll Manager

- [ ] **3-1a. Buy-in 관리**
  - [ ] 현재 활성 buy-in 잔액 추적
  - [ ] buy-in 상태: ACTIVE / BUST / GRADUATED
  - [ ] bust 조건: 잔액 < $25
  - [ ] 승격 조건: 잔액 >= $75 or $100

- [ ] **3-1b. 포지션 사이징**
  - [ ] buy-in 잔액에 따른 max bet 계산
  - [ ] zone별 베팅 비율 적용
  - [ ] 동시 포지션 제한 (max 2)

### Step 3-2: Circuit Breakers

- [ ] **3-2a. 연패 감지**
  - [ ] 최근 N회 연속 패배 추적
  - [ ] 3연패 시 1시간 휴식 타이머

- [ ] **3-2b. 일일 손실 제한**
  - [ ] 당일 누적 손실 추적
  - [ ] buy-in의 30% 초과 시 당일 중단

- [ ] **3-2c. Buy-in bust 처리**
  - [ ] 잔액 < $25 → bust 선언
  - [ ] 다음 buy-in 자동 활성화
  - [ ] 3회 연속 bust → 전체 중단

### Step 3-3: Abnormal Event Handler

- [ ] **3-3a. 데이터 이상 감지**
  - [ ] Binance 데이터 5초 이상 없음 → halt
  - [ ] Polymarket API 5xx → halt + backoff retry
  - [ ] 가격/오즈 방향 충돌 30초+ → halt

- [ ] **3-3b. 자동 복구**
  - [ ] 이상 해소 시 자동 재개
  - [ ] 복구 불가 시 텔레그램 알림

---

## Phase 4: Telegram Bot (Day 6~7)

> 알림 시스템을 연결한다.

- [ ] **4-1. Telegram Bot 초기화**
  - [ ] BotFather로 봇 생성, 토큰 발급
  - [ ] chat_id 확인
  - [ ] `.env`에 토큰/chat_id 저장

- [ ] **4-2. 알림 메시지 구현**
  - [ ] 매수 알림 (🟢 BUY)
  - [ ] 정산 알림 (✅ WIN / ❌ LOSS)
  - [ ] 일일 요약 (📊 Daily Summary)
  - [ ] 서킷브레이커 알림 (🛑)
  - [ ] 이상 이벤트 알림 (⚠️)
  - [ ] 관찰 모드 리포트 (👁️)

- [ ] **4-3. Telegram Bot 테스트**
  - [ ] 각 메시지 타입 전송 확인
  - [ ] 전송 실패 시 재시도 로직
  - [ ] 전송 지연 < 5초 확인

---

## Phase 5: Integration + Main Loop (Day 7~8)

> 모든 모듈을 연결하고 메인 루프를 만든다.

- [ ] **5-1. main.py 작성**
  - [ ] asyncio 기반 메인 루프
  - [ ] 모든 WebSocket 피드 동시 실행
  - [ ] 15분마다 마켓 스캐너 갱신
  - [ ] 시그널 감지 → 주문 실행 파이프라인

- [ ] **5-2. 모드 전환 지원**
  - [ ] `--mode observe`: 관찰 모드 (시그널 기록만)
  - [ ] `--mode paper`: 페이퍼 트레이딩 (가상 매수)
  - [ ] `--mode live`: 실전 모드 (실제 매수)

- [ ] **5-3. graceful shutdown**
  - [ ] Ctrl+C / SIGTERM 시 열린 WebSocket 정리
  - [ ] 현재 상태 SQLite에 저장
  - [ ] 텔레그램으로 종료 알림

- [ ] **5-4. 통합 테스트**
  - [ ] observe 모드로 30분 연속 실행 → 에러 없음
  - [ ] paper 모드로 1시간 실행 → 시그널 감지 + 가상 매수 동작
  - [ ] 로그/DB 기록 정상 확인

---

## Phase 6: Deployment (Day 8~9)

> 서버에 배포하고 24/7 운영을 시작한다.

- [ ] **6-1. 서버 배포**
  - [ ] 서버에 코드 업로드 (scp or git clone)
  - [ ] Python venv + 의존성 설치
  - [ ] `.env` 파일 생성 (API 키 설정)

- [ ] **6-2. systemd 서비스 등록**
  - [ ] `polybot.service` 파일 작성
  - [ ] `systemctl enable polybot`
  - [ ] auto-restart on failure 설정

- [ ] **6-3. 운영 시작**
  - [ ] observe 모드로 첫 24시간 운영
  - [ ] 관찰 데이터로 리플레이 시뮬레이션 실행
  - [ ] Net EV > 0 확인 후 paper 모드 전환
  - [ ] paper 50+ 트레이드 후 live 모드 전환

---

## Phase 7: Validation + Go Live (Day 10+)

> 전략을 검증하고 실전으로 전환한다.

- [ ] **7-1. 리플레이 시뮬레이션**
  - [ ] `replay_sim.py`로 관찰 데이터 시뮬레이션
  - [ ] 가상 승률, 가상 EV, 가상 drawdown 계산
  - [ ] Net EV > 0 이면 PASS

- [ ] **7-2. Paper Trading 검증**
  - [ ] 50+ paper trades 완료
  - [ ] 90%+ zone 승률 >= 88%
  - [ ] 전체 Net EV > 0

- [ ] **7-3. Micro Live ($2.50 bets)**
  - [ ] live 모드 전환 (Caution zone 금액으로 시작)
  - [ ] 50+ 실전 트레이드
  - [ ] 실제 수수료 포함 Net EV 확인

- [ ] **7-4. Full Buy-In ($50)**
  - [ ] 모든 검증 통과 후 정식 운영
  - [ ] 주간 성과 리뷰
  - [ ] 월간 전략 재평가

---

## Quick Reference: 파일 → Phase 매핑

| File | Phase | Priority |
|------|-------|----------|
| `src/config.py` | 0 | 🔴 First |
| `src/market_scanner.py` | 1 | 🔴 |
| `src/price_feed.py` | 1 | 🔴 |
| `src/odds_feed.py` | 1 | 🔴 |
| `src/observer.py` | 1 | 🔴 |
| `src/signal_engine.py` | 2 | 🟡 |
| `src/trade_executor.py` | 2 | 🟡 |
| `src/risk_manager.py` | 3 | 🟡 |
| `src/telegram_bot.py` | 4 | 🟢 |
| `src/state_store.py` | 1~3 | 🟡 (incremental) |
| `src/main.py` | 5 | 🟢 |
| `src/replay_sim.py` | 7 | 🔵 |
