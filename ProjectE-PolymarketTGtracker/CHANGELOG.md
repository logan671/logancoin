# Changelog

## [2026-02-06] Claude Code 수정

### 수정자
- Claude Code (Opus 4.5)

### 문제 분석
폴리마켓 트랜잭션 감지가 작동하지 않는 원인 분석 결과:

1. **핵심 버그**: `w3.codec.decode_abi()` 메서드가 web3.py 6.x에서 존재하지 않음
2. tracker.py:195 라인에서 이벤트 로그 데이터 디코딩 시 에러 발생

### 변경 사항

#### tracker.py
- **Line 7**: `from eth_abi import decode` import 추가
- **Line 195**: `w3.codec.decode_abi(EVENT_TYPES, log["data"])` → `decode(EVENT_TYPES, bytes(log["data"]))` 변경

#### requirements.txt
- `eth_abi>=5.0.0` 의존성 추가

### 기술적 배경
- web3.py 6.x에서는 `w3.codec.decode_abi`가 deprecated/제거됨
- eth_abi 패키지의 `decode()` 함수를 직접 사용해야 함
- `log["data"]`는 HexBytes 타입이므로 `bytes()`로 변환 필요

### 추가 확인 필요 사항 (Codex 참고)
1. **토큰 ID 매핑 검증**: GAMMA API의 `clobTokenIds`와 온체인 `makerAssetId/takerAssetId`가 동일한 형식인지 실제 데이터로 확인 필요
2. **테스트 실행**: 수정 후 실제 지갑 등록하고 트랜잭션 감지되는지 테스트 필요

### 참고 자료
- Polymarket CTF Exchange Contract: https://github.com/Polymarket/ctf-exchange
- web3.py 6.x docs: https://web3py.readthedocs.io/en/v6.20.2/
- OrderFilled Event: `OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)`
  - indexed: orderHash, maker, taker
  - non-indexed: makerAssetId, takerAssetId, makerAmountFilled, takerAmountFilled, fee
