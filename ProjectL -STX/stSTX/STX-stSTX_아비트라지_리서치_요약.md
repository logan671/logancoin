# STX/stSTX 아비트라지 리서치 요약

작성일: 2026-02-19

## 1) 결론 요약

- STX/stSTX 아비트라지는 기술적으로 구현 가능하다.
- 다만 공개된 STX/stSTX 전용 백테스트 자료는 제한적이어서, 실거래 전 자체 백테스트가 필수다.
- 최종 수익성은 유동성, 슬리피지, 수수료, 출금 경로 제약(특히 Instant Unstack 비용) 영향이 크다.

## 2) 왜 기회가 생기는가

- stSTX는 스테이킹 보상이 반영되는 구조라 STX 대비 기준가가 시간에 따라 변화한다.
- 실제 시장 가격(DEX)과 프로토콜 기준 환산가 사이에 괴리가 생길 수 있다.
- 출금/언스택 경로가 복수로 존재해(즉시 스왑, Instant Unstack, 사이클 종료 출금) 가격 괴리 구간이 생긴다.

## 3) 과거 백테스트 현황

- STX/stSTX에 특화된 신뢰 가능한 공개 백테스트는 많지 않다.
- 따라서 전략 검증은 직접 구축하는 편이 현실적이다.
- Curve 계열 스테이블스왑 시뮬레이션 도구(예: curvesim)를 참고해 자체 시뮬레이터를 구성할 수 있다.

## 4) 제품 구현에 필요한 핵심 데이터

- 프로토콜 기준 STX/stSTX 환산가 시계열
- DEX 풀 상태 시계열(리저브, 수수료, 체결가, 유동성 깊이)
- 체결 비용 모델(DEX fee, 네트워크 fee, 실패/재시도 비용)
- 언스택 제약(Instant Unstack 1% 비용, 유동성 가용성, 사이클 타이밍)
- 실행 리스크(지연, 미체결, 프론트런 가능성)

## 5) 구현 가능성 평가

- 기술 구현 난이도: 중간 (데이터 수집/정합성 확보가 핵심)
- 운영 난이도: 중간~높음 (실시간 감시, 리스크 제어 로직 필요)
- 수익성 확률: 데이터 검증 전에는 불확실. 소액 실거래 검증 단계가 필요

## 6) 권장 MVP 순서

1. 관측기: DEX 가격 vs 프로토콜 기준가 괴리 실시간 수집
2. 시뮬레이터: 수수료/슬리피지/지연 반영 백테스트
3. 실행기: 소액 자동 체결 + 리스크 제한
4. 모니터링: PnL, 체결 실패율, 괴리 분포 대시보드

## 7) 참고 링크

- StackingDAO stSTX basics  
  https://docs.stackingdao.com/stackingdao/the-stacking-dao-app/ststx-liquid-stacking-with-stx-rewards/ststx-basics
- StackingDAO withdrawing (Instant Unstack 등)  
  https://docs.stackingdao.com/stackingdao/the-stacking-dao-app/ststx-liquid-stacking-with-stx-rewards/withdrawing-from-ststx
- StackingDAO core contracts  
  https://docs.stackingdao.com/stackingdao/core-contracts/stacking-dao-core-v4
- Stacks stacking 개요  
  https://docs.stacks.co/understand-stacks/stacking
- Hiro Stacks API  
  https://docs.hiro.so/stacks/api/client
- DefiLlama (StackingDAO TVL)  
  https://defillama.com/protocol/stackingdao
- CoinGecko (STSTX)  
  https://www.coingecko.com/en/coins/stacking-dao
- curvesim  
  https://github.com/curveresearch/curvesim

## 8) 다음 단계 제안

- 바로 백테스트 설계서(데이터 스키마, 수집 주기, PnL 계산식) 문서를 추가 작성
- `ProjectL -STX/stSTX` 폴더에 MVP 코드 스켈레톤 생성
