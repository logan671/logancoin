# Bitflow API 및 STX/stSTX 풀 감지 조건

작성일: 2026-02-19

## 1) 핵심 결론

- Bitflow에서 **공개로 바로 조회 가능한 데이터 소스**가 있다.
- STX/stSTX는 현재 ticker 기준으로 복수 풀이 보이며, 유동성/거래량 기준으로 우선순위를 정해 감시 가능하다.
- BFF API(`bff.bitflowapis.finance`)는 문서상 API key 안내가 있으나, 일부 엔드포인트는 현재 공개 조회가 가능했다.

## 2) 확인된 API 엔드포인트

### A. 공개 Ticker API (즉시 사용 가능)

- Base URL: `https://bitflow-sdk-api-gateway-7owjsmt8.uc.gateway.dev`
- Endpoint: `GET /ticker`
- 특징:
  - 코인마켓 스타일 ticker 배열 제공
  - `pool_id`, `liquidity_in_usd`, `base_volume`, `target_volume`, `last_price` 포함
  - STX/stSTX 풀 탐색에 바로 사용 가능

### B. BFF Quotes API

- Docs: `https://bff.bitflowapis.finance/api/quotes/docs`
- OpenAPI: `https://bff.bitflowapis.finance/api/quotes/openapi.json`
- 주요 경로:
  - `/api/quotes/v1/quote`
  - `/api/quotes/v1/quote/multi`
  - `/api/quotes/v1/tokens`
  - `/api/quotes/v1/pools`
  - `/api/quotes/v1/pairs`
  - `/api/quotes/v1/bins/{pool_id}`
  - `/api/quotes/v1/swap`
- 비고:
  - 공식 문서엔 API key 안내가 있으나, 현재 일부 조회는 키 없이 응답됨.
  - 실시간 운영 전에는 key 정책 재확인 필요.

### C. BFF App API

- Docs: `https://bff.bitflowapis.finance/api/app/docs`
- OpenAPI: `https://bff.bitflowapis.finance/api/app/openapi.json`
- 주요 경로:
  - `/api/app/v1/pools`
  - `/api/app/v1/pools/{pool_id}`
  - `/api/app/v1/pools/{pool_id}/activity`
  - `/api/app/v1/tickers`
  - `/api/app/v1/tokens/prices`
- 비고:
  - 현재 응답을 보면 DLMM 중심 데이터가 노출되는 구간이 있어, stableswap 풀은 누락될 수 있음.

## 3) STX/stSTX 관련 풀 (실측)

출처: `GET https://bitflow-sdk-api-gateway-7owjsmt8.uc.gateway.dev/ticker`

1. `SM1793C4R5PZ4NS4VQ4WMP7SKKYVH8JZEWSZ9HCCR.stableswap-pool-stx-ststx-v-1-4`
- `liquidity_in_usd`: `829113.0971887939`
- `base_volume`: `19702.029451`
- `target_volume`: `17126.279074`
- `last_price`: `0.8676765`

2. `SPQC38PW542EQJ5M11CR25P7BS1CA6QT4TBXGB3M.stx-ststx-lp-token-v-1-2`
- `liquidity_in_usd`: `277973.99334835017`
- `base_volume`: `0.0`
- `target_volume`: `0.0`
- `last_price`: `0.0`

3. `SPQC38PW542EQJ5M11CR25P7BS1CA6QT4TBXGB3M.stx-ststx-lp-token-v-1-1`
- `liquidity_in_usd`: `23981.051749136346`
- `base_volume`: `0.0`
- `target_volume`: `0.0`
- `last_price`: `0.0`

해석:
- 현재는 `...stableswap-pool-stx-ststx-v-1-4`를 1순위 감시 대상으로 두는 게 합리적.

## 4) 풀 감지 조건 (봇 룰)

### 1단계: 후보 풀 식별

- 조건 A: `target_currency == SP4SZE...ststx-token` AND `base_currency == Stacks`
- 조건 B: `pool_id` 문자열에 `stx-ststx` 포함
- 조건 C: 동일 pair 복수일 경우 `liquidity_in_usd` 내림차순 정렬

### 2단계: 실행 가능성 필터

- `liquidity_in_usd >= L_min`
- `base_volume_24h >= V_min`
- `last_price > 0`

권장 초기값(튜닝 전 임시):
- `L_min = 200000` USD
- `V_min = 5000` (base 단위)

### 3단계: 아비트라지 신호 결합

- 시장비율(DEX): `market_stx_per_ststx = 1 / last_price` (base=STX, target=stSTX 가정)
- 내재가치(온체인): `intrinsic_stx_per_ststx` (Hiro read-only 계산)
- 신호:
  - `edge_pct = (market_stx_per_ststx / intrinsic_stx_per_ststx - 1) * 100`
- 진입:
  - `|edge_pct| > 비용추정치(수수료+슬리피지+지연)` 일 때만

## 5) 주의점

- ticker의 `bid/ask`가 비어 있는 경우가 있어 스프레드 기반 필터만으로는 부족하다.
- 실제 실행 전엔 풀 리저브 기반 슬리피지 추정(주문 수량별)을 별도로 계산해야 한다.
- API 스펙/권한 정책은 변경될 수 있으니 운영 투입 전 재검증 필요.
