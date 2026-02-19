# STX/stSTX 1차 스크리닝 (내재가치 기준)

작성 시각: 2026-02-19 (UTC 기준 API 조회)

## 1) 결론 요약

- 코인게코 가격만으로는 실제 체결 가능한 차익거래를 확정할 수 없다.
- 다만 1차 스크리닝은 가능하며, 온체인 내재가치와 붙이면 후보 구간 필터링 정확도가 올라간다.
- 이번 실시간 샘플에서 시장 비율은 내재가치 대비 약 `-0.1637%` (소폭 디스카운트)였다.

## 2) 코인게코 기반 30일 비율 스크리닝 (daily)

- 대상: `blockstack(STX)`, `stacking-dao(stSTX)`
- 지표: `ratio = stSTX_USD / STX_USD`

요약 통계:
- 관측치: `30`
- 평균 비율: `1.151299`
- 최소 비율: `1.133354` (2026-02-02)
- 최대 비율: `1.167049` (2026-02-06)

해석:
- 최근 30일 내에서 `stSTX/STX` 비율 변동 폭은 약 `2.97%p` 수준(최대-최소).
- 이 값 자체는 "가격 괴리 후보"를 찾는 용도이며, 실제 체결 가능성은 DEX 유동성과 슬리피지 확인이 필요.

## 3) stSTX 내재가치 실시간 조회 가능 여부

가능하다. Hiro의 Stacks read-only API를 통해 필요한 원시 값을 바로 읽을 수 있다.

핵심 컨트랙트:
- Core V6: `SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG.stacking-dao-core-v6`
- Data Core V3: `SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG.data-core-v3`

Data Core V3 소스 기준 계산식:
- `stx_for_ststx = total_stx_amount - ststxbtc_supply - ststxbtc_supply_v2`
- `intrinsic_stx_per_ststx = stx_for_ststx * 1e6 / ststx_supply`

여기서 필요한 실시간 read-only 값:
- `reserve-v1/get-total-stx`
- `ststx-token/get-total-supply`
- `ststxbtc-token/get-total-supply`
- `ststxbtc-token-v2/get-total-supply`

## 4) 실시간 샘플 계산 (조회 시점 기준)

온체인 값(uSTX/ustSTX 단위):
- `reserve_total_stx = 84,740,186,428,963`
- `ststx_supply = 45,855,205,988,850`
- `ststxbtc_supply = 0`
- `ststxbtc_v2_supply = 31,629,486,029,612`
- `stx_for_ststx = 53,110,700,399,351`

산출:
- `intrinsic_stx_per_ststx = 1.15822619`

동일 시점 코인게코:
- `market_stx_per_ststx = stSTX_USD / STX_USD = 1.15633042`

비교:
- `market_vs_intrinsic = -0.1637%`

해석:
- 조회 시점 기준으로는 시장 비율이 내재가치보다 소폭 낮았다(디스카운트).
- 이 정도 차이는 수수료/슬리피지/체결 지연을 고려하면 바로 실행 신호로 보기 어렵다.

## 5) 봇 신호로 쓰는 방법 (권장)

내가 추천하는 1차 신호:
- `edge_pct = (market_stx_per_ststx / intrinsic_stx_per_ststx - 1) * 100`
- 임계치 예시: `|edge_pct| >= 비용추정치 + 안전마진`

주의:
- 너가 말한 대로 1% Instant Unstack 기준을 고정 하드코딩할 필요는 없다.
- 대신 내재가치 기준 괴리(`edge_pct`)를 주 신호로 두고, 실행 단계에서 가능한 경로별 비용을 동적으로 반영하는 구조가 더 맞다.

## 6) 참고 소스

- StackingDAO Core V6 문서  
  https://docs.stackingdao.com/stackingdao/core-contracts/ststx-stacking-dao-core-v6
- Core V6 컨트랙트 소스(Hiro API)  
  https://api.hiro.so/v2/contracts/source/SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG/stacking-dao-core-v6?proof=0
- Data Core V3 컨트랙트 소스(Hiro API)  
  https://api.hiro.so/v2/contracts/source/SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG/data-core-v3?proof=0
- CoinGecko simple price  
  https://api.coingecko.com/api/v3/simple/price?ids=blockstack,stacking-dao&vs_currencies=usd
