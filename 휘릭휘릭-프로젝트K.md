# 휘릭휘릭-프로젝트K (실전/서버 운영 버전)

## 1. 이 프로젝트를 한 줄로
- 목표: **서버가 24시간 자동으로** 특정 지갑 거래를 감지하고, 내 팔로워 지갑이 조건대로 따라 거래하게 만들기.
- 핵심: 웹은 조회만, 등록은 텔레그램, 비밀키는 서버 볼트에만 저장.

---

## 2. 가장 중요한 원칙 3개
- 니모닉/프라이빗키는 텔레그램에 절대 입력하지 않는다.
- 텔레그램/DB/웹에는 `key_ref(vault://...)`만 사용한다.
- 로컬은 테스트용, **실제 운영은 서버 프로세스(systemd/supervisor)**로 돌린다.

---

## 3. 실전 아키텍처 (쉽게)
1. 지갑 비밀값 등록
- 서버에서 `wallet_cli`로 니모닉을 암호화 저장.
- 결과로 `vault://wallet_1` 같은 이름표(`key_ref`)를 받음.

2. 페어 등록
- 텔레그램 `/addpair` 대화형으로 source/follower/budget/key_ref 입력.
- 이때 `key_ref`가 볼트에 없으면 등록 실패.

3. 거래 감지
- watcher/worker가 source 지갑 거래를 감지해 신호 생성.

4. 주문 생성
- mirror order 생성, 슬리피지/예산/실패횟수 정책 검사.

5. 실제 실행 (여기가 핵심)
- 실거래 executor가 `key_ref`로 볼트에서 키를 읽고 서명.
- Polymarket/CLOB 경로로 주문 전송.
- 결과를 `executions`에 기록.

6. 사후 처리
- 실패 알림 텔레그램 전송.
- (옵션) 마켓 종료 후 자동 claim 워커로 정산.

---

## 4. 지금 코드 상태 vs 실전 목표
- 지금: stub executor(가짜 체결 기록).
- 목표: real executor(실제 트랜잭션/주문 전송).

실전 전환에 필요한 구현 항목:
- `worker/signal_worker.py`의 stub 분기를 real executor 호출로 교체.
- 체결 결과를 거래소/API 응답 기준으로 저장.
- 재시도/타임아웃/부분체결/취소 로직 추가.

---

## 5. 서버 기준 실행 흐름 (운영 순서)
### Step 1) 서버에 볼트 비밀번호 설정
- 예: `PROJECTK_VAULT_PASSPHRASE`
- 용도: 니모닉 암복호화 마스터 키

### Step 2) 팔로워 지갑 니모닉 등록
- `python3 -m backend.wallet_cli add wallet_1`
- 결과: `vault://wallet_1`

### Step 3) API/등록봇/워커/웹 서버 프로세스 실행
- 서버 부팅 후 자동 재시작되도록 서비스 등록(systemd 권장)
- **실거래 모드로 돌릴 때는 워커 환경변수에 아래를 추가**
  - `PROJECTK_EXECUTOR_MODE=live`
  - `PROJECTK_VAULT_PASSPHRASE=...`
  - `PROJECTK_POLYMARKET_HOST=https://clob.polymarket.com`
  - `PROJECTK_POLYMARKET_CHAIN_ID=137`
  - `PROJECTK_POLYMARKET_SIGNATURE_TYPE=0`

### Step 4) 텔레그램에서 페어 등록
- `/addpair` 입력 후 질문에 순서대로 답
- key_ref 질문에서 `vault://wallet_1` 입력

### Step 5) 실신호 유입/실행 모니터링
- 대시보드: 페어/주문/실행 상태 확인
- 텔레그램: 실패 알림 확인

---

## 6. 네가 자주 헷갈리는 포인트 정리
- `budget_usdc`: 이 팔로워 지갑 페어에 배정한 운영 예산
- `key_ref`: 비밀키 자체가 아니라, 비밀키를 찾는 이름표
- 왜 owner chat id 필요?: 아무나 등록/삭제 못 하게 관리자 본인만 허용하기 위해

---

## 7. 실전 리스크 가드 (반드시 켜기)
- 슬리피지 상한: 3% (300 bps)
- 연속 실패 차단: 3회
- 가스(MATIC) 부족 알림: 0.5 미만
- 주문 최소금액: Polymarket 최소 주문 규칙 이상으로 설정
- 일일 손실 한도(추가 권장): 예산의 X%

---

## 8. 자동 Claim은 가능한가?
- 가능.
- 조건: 마켓 최종 확정 후, 보유 포지션 정산 트랜잭션 호출.
- 구현 권장:
  - `claim_worker`를 별도 프로세스로 분리
  - 일정 주기/이벤트 기반으로 claim 가능 상태 검사
  - 성공/실패/재시도 기록 + 텔레그램 알림

---

## 9. 서버 운영 체크리스트 (실전 전)
- [ ] 볼트 비밀번호를 `.env` 또는 시크릿 매니저로 관리
- [ ] 텔레그램 토큰/오너ID 환경변수 적용
- [ ] 서비스 자동시작/재시작 설정
- [ ] 로그 로테이션 설정
- [ ] 백업(DB + 설정) 암호화
- [ ] 비상 정지 방법 준비(모든 페어 active=0 또는 워커 중지)

---

## 10. 다음 구현 우선순위 (실전 전환 로드맵)
1. Real executor 모듈 추가 (서명/주문/체결조회)
2. claim worker 추가
3. 서비스 배포 스크립트(systemd unit + healthcheck)
4. 운영 대시보드에 잔고/가용 예산/최근 오류율 표시

---

## 11. 너는 이렇게 말하면 됨
- “실거래 executor부터 붙여줘”
- “claim worker도 같이 붙여줘”
- “서버 배포용 systemd 파일까지 만들어줘”
