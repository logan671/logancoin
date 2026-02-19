# ProjectK Security Policy

## 1) 목표
- 서버 운영 시 private key / mnemonic이 코드, DB, 로그, 화면에 노출되지 않게 한다.

## 2) 현재 구현 상태
- DB에는 `follower_wallets.key_ref`만 저장한다.
- 즉, 현재 DB에는 private key 평문이 들어가지 않는다.
- 로그/알림 메시지에도 private key/mnemonic을 출력하지 않는다.
- `vault_keys` 테이블에는 니모닉을 암호화한 blob만 저장한다.
- 텔레그램 등록은 `key_ref(vault://...)`만 받는다.

## 3) 금지 사항
- `seed.sql`/`schema.sql`/코드 파일에 private key 하드코딩 금지
- 텔레그램 알림/웹 화면/로그에 mnemonic 출력 금지
- 운영 문서/메모 파일에 비밀키 평문 기록 금지

## 4) 서버 운영 권장 방식
- 키는 서버 DB가 아닌 별도 vault 계층에서 관리
- 애플리케이션은 `key_ref`로만 키를 조회
- 운영 계정 권한 분리:
  - 앱 실행 계정
  - DB 계정
  - 배포 계정
- 환경변수 파일 권한 최소화 (`chmod 600`)

## 5) 최소 운영 체크리스트
- [ ] DB dump에서 mnemonic/private key 문자열이 검색되지 않는가
- [ ] 텔레그램 알림에 민감정보가 포함되지 않는가
- [ ] 로그 파일에 `key`, `mnemonic`, `private` 노출이 없는가
- [ ] 서버 사용자별 접근권한이 분리되어 있는가
- [ ] 백업 파일도 암호화되어 있는가

## 6) 실전 전 필수 고지
- 현재 executor는 stub(테스트 실행기)이며, 실제 서명/주문 엔진이 아니다.
- 실전 체결을 위해서는 별도 실거래 executor + vault 연동이 추가되어야 한다.
