# Project Rules

## Rule 0: 한영 오타 자동 해독 (최우선)

유저가 한영키 전환을 실패해서 영어 자판으로 한국어를 타이핑하는 경우가 자주 발생한다.
**의미 없는 영어가 나오면 무조건 한글 자판 배열로 변환해서 해독하라.**

판별 기준:
- 영어인데 단어가 하나도 안 되는 경우 → 100% 한영 오타
- 한국어 문장 중간에 갑자기 영어 덩어리가 섞인 경우 → 한영 오타

변환 방법 (영어 키 → 한글):
```
q=ㅂ w=ㅈ e=ㄷ r=ㄱ t=ㅅ y=ㅛ u=ㅕ i=ㅑ o=ㅐ p=ㅔ
a=ㅁ s=ㄴ d=ㅇ f=ㄹ g=ㅎ h=ㅗ j=ㅓ k=ㅏ l=ㅣ
z=ㅋ x=ㅌ c=ㅊ v=ㅍ b=ㅠ n=ㅜ m=ㅡ
Q=ㅃ W=ㅉ E=ㄸ R=ㄲ T=ㅆ O=ㅒ P=ㅖ
```

**처리 방식: 키보드 직접 입력처럼 동작하라.**
- 1:1 자모 치환만 수행하고, IME 조합 시뮬레이션은 하지 마라.
- 자모 스트림을 나열한 뒤 한국어 이해력으로 바로 읽어라.
- 예: `todrkrgksms` → `ㅅㅐㅇㄱㅏㄱㅎㅏㄴㅡㄴ` → "생각하는" (조합 과정 생략)
- 이 방식으로 긴 문장도 빠르게 처리하고 토큰을 절약한다.

**변환 후 해독한 내용을 기반으로 자연스럽게 대화를 이어가라.**
해독이 애매하면 "혹시 ~~ 이런 말이야?" 하고 확인하라.

## Rule 1: 코드/명령어는 휘릭휘릭메모장.md에 작성

터미널에서 직접 실행하면 줄바꿈 복붙 에러가 발생한다.
코드나 명령어를 전달해야 할 때는 `휘릭휘릭메모장.md` 파일의 `## 복붙용 명령어` 섹션에 작성하라.
유저가 복사해서 터미널에 붙여넣기 편하도록 코드블록(```)으로 감싸서 작성한다.

- 한 번에 실행할 명령어는 하나의 코드블록에 넣는다
- 여러 단계일 경우 단계별로 코드블록을 나눈다
- 이전에 작성한 복붙용 명령어는 지우고 최신 것만 유지한다

## Rule 2: 모든 명령어를 설명하라

터미널 명령어가 등장할 때마다 반드시 다음을 설명하라:

1. **이 명령어가 뭐 하는 건지** (한 줄 요약)
2. **지금 우리가 무슨 작업을 하고 있는 건지** (전체 흐름에서의 위치)

유저가 "앞으로 명령어 설명하지 마"라고 말하기 전까지 이 규칙을 계속 지킨다.

예시:
> `npm install express` - express 웹 서버 라이브러리를 설치하는 명령어.
> 지금 우리는 ProjectA의 백엔드 서버를 세팅하는 중이고, 이게 첫 번째 단계야.

## Rule 3: 배포 타깃 명시 (전역 대규칙)

서버/배포/운영 관련 작업은 반드시 `target`을 명시한다.

- 허용 값: `company` 또는 `personal`
- 자연어 매핑:
  - "회사서버", "회사 서버" -> `company`
  - "개인서버", "개인 서버" -> `personal`
- `target`이 없거나 애매하면 작업을 중단하고 사용자에게 재확인한다.
- 사용자가 "서버에 올려줘"처럼 target 없이 지시하면, 반드시 "company 또는 personal 중 어디로 배포할지"를 되묻는다.
- 배포 전 반드시 `DEPLOY_TARGETS.yaml`을 확인한다.

## 설명 생략 명령어

유저 요청에 따라 아래 명령어는 설명을 생략한다.

- scp
- ssh

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

## General

- 유저와의 소통은 한국어로 한다
- 코드 주석은 영어로 작성한다
- 이 폴더는 여러 서브 프로젝트를 포함하는 모노레포 구조다
- 각 프로젝트별 상세 규칙은 해당 프로젝트 폴더의 CLAUDE.md를 참고하라

## Project Map

| 폴더 | 설명 |
|------|------|
| ProjectA-PolymarketTop7topic | Polymarket 한글화 커뮤니티 서비스 (Mm.pro) |
| ProjectC-Polymarketnewrecommendation | Polymarket 신규 마켓 추천 |
| ProjectD-forumdesignforuser | 포럼 디자인 |
| ProjectE-PolymarketTGtracker | Polymarket 텔레그램 트래커 |
| ProjectF-kimchithumbnail(team agent) | 김치 썸네일 생성 |
| ProjectG-15minpolybetter | Polymarket 15분 크립토 모멘텀 트레이딩 봇 |

## Server

- 배포 서버: 47.80.2.58 (Ubuntu 24.04, 4 vCPU, 7GB RAM)
- 서버 상세 정보: `SERVER_INFO.md`, `SERVER_SPECS.md` 참고
- 민감 정보(API 키, 비밀번호 등)를 코드에 하드코딩하지 마라

## GitHub SSH 설정

- 이 저장소는 GitHub SSH 인증을 사용한다 (HTTPS 토큰 방식 아님).
- 원격 `origin`: `git@github.com:logan671/logancoin.git`
- SSH 공개키 fingerprint: `SHA256:tOEY83qfXpEsjHIHPSA10vicQ7CNUzs2b2pteKT4E0s`
- 개인키(Private key)는 절대 기록/공유하지 않는다.
- 이 저장소의 주요 사용 개발자는 개발을 시작한 지 1주도 안 된 초보자다.
- 커밋 메시지는 기본적으로 날짜/시간 형식(`YYMMDD HHAM/PM`)을 사용한다.
- 에이전트/작업자 태그를 커밋 메시지 끝에 괄호로 추가한다. 예: `260212 11AM (Codex)`
