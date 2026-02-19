# Project Rules

이 파일은 OpenAI Codex 등 AI 에이전트를 위한 규칙 파일이다.
상세 규칙은 `CLAUDE.md`와 동일하므로 해당 파일을 반드시 함께 읽어라.

## 용어 어원(간단)

- **scp**: *secure copy*의 약자. SSH 기반으로 파일을 안전하게 복사.
- **ssh**: *secure shell*의 약자. 서버에 안전하게 원격 접속.
- **systemctl**: systemd를 제어하는 *system control* 도구.
- **daemon**: background에서 동작하는 프로세스. 그리스 신화의 *daimon*에서 유래.
- **service**: systemd가 관리하는 실행 단위.
- **timer**: systemd에서 주기 실행을 담당.
- **cron**: 그리스어 *chronos*(시간)에서 유래. 주기 작업 스케줄러.
- **cache**: 프랑스어 *cacher*(숨기다)에서 유래. 자주 쓰는 데이터를 임시 저장.
- **API**: *Application Programming Interface*의 약자. 프로그램끼리 통신하는 규칙.
- **RPC**: *Remote Procedure Call*의 약자. 원격 함수 호출.
- **DB**: *Database*의 약자. 구조화된 데이터 저장소.
- **SQL**: *Structured Query Language*의 약자. DB 질의 언어.
- **JSON**: *JavaScript Object Notation*의 약자. 경량 데이터 포맷.

## Rule 1: 코드/명령어는 휘릭휘릭메모장.md에 작성

터미널에서 직접 실행하면 줄바꿈 복붙 에러가 발생한다.
코드나 명령어를 전달해야 할 때는 `휘릭휘릭메모장.md` 파일의 `## 복붙용 명령어` 섹션에 작성하라.
유저가 복사해서 터미널에 붙여넣기 편하도록 코드블록(```)으로 감싸서 작성한다.

## Rule 2: 모든 명령어를 설명하라

터미널 명령어가 등장할 때마다 반드시 다음을 설명하라:

1. **이 명령어가 뭐 하는 건지** (한 줄 요약)
2. **지금 우리가 무슨 작업을 하고 있는 건지** (전체 흐름에서의 위치)

유저가 "앞으로 명령어 설명하지 마"라고 말하기 전까지 이 규칙을 계속 지킨다.

## Rule 3: 배포 타깃 명시 (전역 대규칙)

서버/배포/운영 관련 작업은 반드시 `target`을 명시한다.

- 허용 값: `company` 또는 `personal`
- 자연어 매핑:
  - "회사서버", "회사 서버" -> `company`
  - "개인서버", "개인 서버" -> `personal`
- `target`이 없거나 애매하면 작업을 중단하고 사용자에게 재확인한다.
- 사용자가 "서버에 올려줘"처럼 target 없이 지시하면, 반드시 "company 또는 personal 중 어디로 배포할지"를 되묻는다.
- 배포 전 반드시 `DEPLOY_TARGETS.yaml`을 확인한다.

## General

- 유저와의 소통은 한국어로 한다
- 코드 주석은 영어로 작성한다
- 민감 정보(API 키, 비밀번호 등)를 코드에 하드코딩하지 마라
- 서버/프로젝트 상세: `CLAUDE.md` 참고
