# Polymarket Alpha Scanner

Polymarket 신규 마켓에서 알파(mispricing) 기회를 자동으로 탐지하는 도구.

## Features

### 2단계 AI 분석
```
신규 마켓 500개/월
      ↓
[1차 스크리닝] GPT-4o-mini (저비용)
  "알파 가능성 있어?" → 10-15% 통과
      ↓
[2차 딥리서치] Perplexity Sonar Pro (웹검색)
  "진짜 확정 수익 기회?" → 알파 점수 계산
      ↓
텔레그램 알림 + 웹 대시보드
```

### 알파 유형
- **Type A (팩트체크)**: 이미 결과가 확정된 마켓
- **Type B (확률)**: 높은 확률로 예측 가능한 마켓

### 웹 대시보드
- 신규 마켓 목록 (한글 번역)
- 즐겨찾기 기능
- 스크리닝 통과/패스 필터
- **피드백 시스템**: AI가 학습하는 규칙 생성

## Quick Start

### 1. 설치

```bash
cd ProjectC-Polymarketnewrecommendation

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일 수정:
```bash
# 1차 스크리닝 (필수)
OPENAI_API_KEY=sk-your-key-here

# 2차 딥리서치 (권장)
PERPLEXITY_API_KEY=pplx-your-key-here

# 텔레그램 알림 (선택)
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

### 3. 실행

```bash
# 웹 대시보드 실행 (http://localhost:8000)
python run.py --web

# 스케줄러 모드 (5분마다 스캔)
python run.py

# 한 번만 실행 (테스트용)
python run.py --once
```

## 웹 대시보드

`http://localhost:8000` 접속

### 기능
| 탭 | 설명 |
|----|------|
| 최신 마켓 | 최근 발견된 마켓 |
| 높은 알파 | 알파 점수 50+ 마켓 |
| 스크리닝 통과 | 1차 통과한 마켓 |
| 패스됨 | 스킵된 마켓 |
| 즐겨찾기 | 저장한 마켓 |

### 피드백 시스템
사이드바에서 피드백 입력 → AI 학습에 반영

| 타입 | 설명 |
|------|------|
| 이런 거 추천 안해줘 | 자동으로 학습 규칙 생성 |
| 좋은 추천이었어 | 긍정 피드백 기록 |
| 잘못된 추천이었어 | 부정 피드백 기록 |

## API 키 발급

### OpenAI
1. https://platform.openai.com/api-keys
2. API 키 생성 → `OPENAI_API_KEY`

### Perplexity
1. https://www.perplexity.ai/settings/api
2. API 키 생성 → `PERPLEXITY_API_KEY`

### Telegram
1. [@BotFather](https://t.me/botfather)에서 봇 생성
2. 봇 토큰 → `TELEGRAM_BOT_TOKEN`
3. 봇에게 메시지 후 Chat ID 확인:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

## 예상 비용

| 단계 | 마켓 수 | 월 비용 |
|------|--------|--------|
| 1차 스크리닝 | 500개 | ~$0.50 |
| 2차 딥리서치 | 50개 | ~$2-5 |
| **총합** | | **$3-8/월** |

## 프로젝트 구조

```
ProjectC-Polymarketnewrecommendation/
├── config/
│   └── settings.py
├── src/
│   ├── main.py              # 메인 실행
│   ├── models.py            # DB 모델
│   ├── database.py          # SQLite
│   ├── polymarket_client.py # Polymarket API
│   ├── market_analyzer.py   # 2단계 AI 분석
│   ├── telegram_notifier.py # 텔레그램
│   └── web/
│       ├── api.py           # FastAPI
│       └── static/
│           └── index.html   # 웹 UI
├── data/                    # DB 파일
├── run.py
├── requirements.txt
└── .env
```

## 주의사항

- API 비용 발생 (월 $3-8 예상)
- 투자 결정은 본인 책임
- 개인 용도로만 사용
