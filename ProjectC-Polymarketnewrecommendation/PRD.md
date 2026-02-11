# PRD: Polymarket 신규 마켓 알파 탐지 시스템

## 1. 개요

### 1.1 프로젝트 명
**Polymarket New Market Alpha Scanner**

### 1.2 문제 정의
- Polymarket에 신규 마켓이 등록되는 순간이 가장 큰 알파(정보 비대칭) 기회
- 신규 마켓은 초기 유동성이 낮고, 시장 참여자가 적어 mispricing 발생 가능성 높음
- **두 가지 유형의 알파 기회 존재:**

#### Type A: 이미 확정된 결과 (Fact-Check Alpha)
- 이미 결과가 발표/확정되었으나 마켓이 뒤늦게 열린 경우
- 예: 이미 발표된 경제지표, 확정된 정책 결정, 종료된 경기 결과

#### Type B: 높은 확률로 예측 가능 (Probability Alpha)
- 결과는 미정이지만, 상식/데이터로 압도적 확률 예측 가능
- 예시:
  - **스포츠**: 리그 1위 vs 꼴찌 → 1위 승리 확률 극히 높음
  - **정치**: 여론조사 70% vs 10% → 앞선 후보 유리
  - **경제**: FED가 50bp 인상할 가능성? → CME FedWatch 0%면 NO 확정적
  - **상식**: "2025년에 인간이 화성 착륙?" → 기술적으로 불가능

### 1.3 목표
1. Polymarket 신규 마켓 실시간 감지
2. AI 기반 알파 기회 자동 분석
3. 고확률 기회 발견 시 즉시 텔레그램 알림
4. 개인용 대시보드에서 모니터링

---

## 2. 핵심 기능

### 2.1 신규 마켓 크롤링 & 모니터링
```
[Polymarket API/Web] → [Crawler] → [New Market DB] → [Dashboard]
                                  ↓
                            [AI Analyzer]
                                  ↓
                          [Telegram Alert]
```

| 기능 | 설명 |
|------|------|
| 실시간 폴링 | Polymarket API를 주기적으로 호출 (1-5분 간격) |
| 신규 마켓 감지 | 이전에 없던 마켓 ID 발견 시 신규로 판정 |
| 메타데이터 수집 | 마켓명, 설명, 마감일, 현재 확률, 거래량 등 |

### 2.2 AI 기반 알파 분석
| 기능 | 설명 |
|------|------|
| 마켓 분류 | 정치/경제/스포츠/크립토/기타 자동 분류 |
| 팩트체크 | 이미 결과가 나온 이벤트인지 웹 검색으로 확인 |
| 확률 평가 | AI가 예상하는 실제 확률 vs 현재 시장 확률 비교 |
| 알파 점수 | 기회의 크기를 0-100 점수로 산출 |

#### 알파 탐지 시나리오 예시

**Type A: 팩트체크 알파 (이미 결과 확정)**
| 시나리오 | AI 분석 | 알파 |
|----------|---------|------|
| "한국 2025 Q1 GDP 음수?" | 한국은행 4/25 발표: -0.2% 확정 | YES 매수 (거의 확정) |
| "손흥민 24/25 시즌 10골 이상?" | 이미 12골 기록 확인 | YES 매수 (확정) |
| "애플 2025 Q1 실적 발표됨?" | 이미 1/30 발표 완료 | YES 매수 (확정) |

**Type B: 확률 알파 (높은 확률 예측)**
| 시나리오 | AI 분석 | 알파 |
|----------|---------|------|
| "맨시티 vs 강등권 팀 경기" | 최근 5시즌 상대전적 19승 1패 | 맨시티 승 85%+ |
| "FED 3월 50bp 인상?" | CME FedWatch 0%, 시장 컨센서스 동결 | NO 95%+ |
| "바이든 2028 대선 출마?" | 86세, 이미 불출마 선언 | NO 95%+ |
| "비트코인 2025년 $1M 돌파?" | 현재 $50K, 20배 상승 비현실적 | NO 90%+ |
| "한국 2025 출산율 1.0 이상?" | 2024년 0.72, 반등 불가능 | NO 95%+ |

**SKIP 케이스 (분석 어려움)**
| 시나리오 | 이유 |
|----------|------|
| "트럼프 2025년 탄핵?" | 정치적 불확실성 높음 |
| "BTC 6개월 후 가격?" | 변동성 예측 불가 |
| "특정 CEO 사임?" | 내부 정보 필요 |

### 2.3 알림 시스템
| 조건 | 알림 |
|------|------|
| 알파 점수 80+ | 즉시 텔레그램 알림 (긴급) |
| 알파 점수 50-79 | 일반 알림 |
| 알파 점수 50 미만 | 대시보드에만 표시 |

#### 텔레그램 알림 포맷

**Type A (팩트체크) 알림:**
```
🚨 FACT-CHECK ALPHA 🚨

📊 마켓: Will South Korea Q1 2025 GDP be negative?
🏷️ 타입: TYPE A (이미 결과 확정)
💰 현재 YES: 12% / NO: 88%
🎯 AI 예측: YES 98%
📈 알파 점수: 92/100

✅ 확정 근거:
한국은행이 2025.04.25 발표한 속보치에 따르면
Q1 GDP 성장률은 -0.2%로 이미 음수 확정.

📎 소스: https://bok.or.kr/...
🔗 https://polymarket.com/event/xxx

⏰ 마켓 마감: 2025-05-15
📉 거래량: $45,230
```

**Type B (확률) 알림:**
```
🔥 PROBABILITY ALPHA 🔥

📊 마켓: Man City vs Southampton - City Win?
🏷️ 타입: TYPE B (높은 확률 예측)
💰 현재 YES: 55% / NO: 45%
🎯 AI 예측: YES 88%
📈 알파 점수: 78/100

📊 근거:
- 맨시티 리그 1위, 사우샘튼 20위(꼴찌)
- 최근 5시즌 상대전적: 맨시티 19승 1패
- 홈경기 승률 94%

⚠️ 리스크: 컵대회 로테이션 가능성

🔗 https://polymarket.com/event/xxx
⏰ 경기 시간: 2025-02-15 21:00 KST
```

### 2.4 개인 대시보드
| 기능 | 설명 |
|------|------|
| 신규 마켓 리스트 | 최근 24시간 내 오픈된 마켓 목록 |
| 알파 점수 정렬 | 높은 점수순 정렬 |
| 필터링 | 카테고리별, 점수별 필터 |
| 상세 분석 | 각 마켓별 AI 분석 결과 확인 |
| 히스토리 | 과거 알림 및 성과 추적 |

---

## 3. 기술 스택 (제안)

### 3.1 Backend
| 컴포넌트 | 기술 | 이유 |
|----------|------|------|
| 런타임 | Python 3.11+ | AI 라이브러리 호환성 |
| 웹 프레임워크 | FastAPI | 비동기, 빠른 개발 |
| 스케줄러 | APScheduler / Celery | 주기적 크롤링 |
| DB | SQLite → PostgreSQL | 초기 간단히, 확장 시 변경 |
| AI | OpenAI GPT-4 API | 분석 품질 |
| 웹 검색 | Tavily API / SerpAPI | 팩트체크용 |

### 3.2 Frontend
| 컴포넌트 | 기술 | 이유 |
|----------|------|------|
| 프레임워크 | Next.js / React | 빠른 개발 |
| 스타일 | Tailwind CSS | 심플한 UI |
| 호스팅 | Vercel / 자체 서버 | 무료 티어 활용 |

### 3.3 Infrastructure
| 컴포넌트 | 기술 |
|----------|------|
| 서버 | 자체 서버 / AWS EC2 / Railway |
| 알림 | Telegram Bot API |
| 모니터링 | 간단한 로깅 |

---

## 4. 데이터 모델

### 4.1 Market
```python
class Market:
    id: str                    # Polymarket 마켓 ID
    title: str                 # 마켓 제목
    description: str           # 상세 설명
    category: str              # 분류 (politics/economics/sports/crypto/other)
    end_date: datetime         # 마감일
    created_at: datetime       # 생성일
    polymarket_url: str        # 마켓 URL

    # 시장 데이터
    yes_price: float           # YES 가격 (0-1)
    no_price: float            # NO 가격 (0-1)
    volume: float              # 거래량 (USD)
    liquidity: float           # 유동성

    # AI 분석 결과
    alpha_type: str            # TYPE_A_FACT | TYPE_B_PROBABILITY | UNCERTAIN
    is_already_resolved: bool  # 이미 결과가 나온 이벤트인지
    ai_prediction: float       # AI 예측 확률 (0-1)
    ai_confidence: float       # AI 신뢰도 (0-100)
    alpha_score: int           # 알파 점수 (0-100)
    price_gap: float           # |AI예측 - 시장가격|
    recommendation: str        # STRONG_BUY_YES/NO, BUY_YES/NO, HOLD, SKIP
    analysis_summary: str      # 분석 요약
    key_evidence: list[str]    # 핵심 근거
    sources: list[str]         # 참고 소스 URL
    risk_factors: list[str]    # 리스크 요인

    # 상태
    is_alerted: bool           # 알림 발송 여부
    alert_sent_at: datetime    # 알림 발송 시각
```

### 4.2 Alert
```python
class Alert:
    id: str
    market_id: str
    alpha_score: int
    message: str
    sent_at: datetime
    telegram_message_id: str
```

---

## 5. AI 분석 프롬프트 설계

### 5.1 마켓 분석 프롬프트
```
You are an expert prediction market analyst specializing in finding alpha opportunities.

**Market Title:** {title}
**Description:** {description}
**Current YES Price:** {yes_price}
**Current NO Price:** {no_price}
**End Date:** {end_date}
**Volume:** {volume}

## Your Analysis Framework

### Step 1: Classify Alpha Type
Determine which type of alpha opportunity this might be:

**Type A (Fact-Check Alpha):** Has this event ALREADY occurred?
- Check if results are already announced/confirmed
- Look for official sources, news reports, statistics
- Examples: GDP already released, match already played, election results announced

**Type B (Probability Alpha):** Is the outcome highly predictable?
- Historical data strongly favors one outcome
- Expert consensus is overwhelming (>85%)
- Common sense makes one outcome near-impossible
- Examples: Top team vs bottom team, demographic trends, physical impossibilities

### Step 2: Gather Evidence
- Search for recent news and official announcements
- Check historical data and statistics
- Look for expert opinions and consensus
- Verify with multiple sources

### Step 3: Calculate True Probability
Based on your research, estimate the ACTUAL probability.

### Step 4: Identify Mispricing
Compare your estimate to market price. Large gaps = alpha opportunity.

## Output JSON:
{
  "alpha_type": "TYPE_A_FACT|TYPE_B_PROBABILITY|UNCERTAIN",
  "category": "politics|economics|sports|crypto|entertainment|other",
  "is_already_resolved": true/false,
  "ai_prediction": 0.0-1.0,
  "market_price": 0.0-1.0,
  "price_gap": 0.0-1.0,
  "confidence": 0-100,
  "alpha_score": 0-100,
  "reasoning": "Step-by-step explanation",
  "key_evidence": ["evidence1", "evidence2"],
  "key_sources": ["url1", "url2"],
  "recommendation": "STRONG_BUY_YES|BUY_YES|HOLD|BUY_NO|STRONG_BUY_NO|SKIP",
  "risk_factors": ["risk1", "risk2"]
}
```

### 5.2 알파 점수 계산 로직
```python
def calculate_alpha_score(market_price, ai_prediction, confidence):
    """
    알파 점수 계산
    - price_diff: 시장가격과 AI예측의 차이 (0-1)
    - confidence: AI 신뢰도 (0-100)
    """
    price_diff = abs(ai_prediction - market_price)

    # 가격 차이가 클수록, 신뢰도가 높을수록 점수 높음
    raw_score = price_diff * confidence

    # 0-100 스케일로 정규화
    alpha_score = min(100, int(raw_score * 1.5))

    return alpha_score
```

---

## 6. 개발 단계

### Phase 1: MVP (1-2주)
- [ ] Polymarket API 연동 및 신규 마켓 감지
- [ ] 기본 DB 저장 (SQLite)
- [ ] GPT-4 연동하여 기본 분석
- [ ] 텔레그램 봇 알림 구현
- [ ] 간단한 CLI 모니터링

### Phase 2: 대시보드 (1-2주)
- [ ] 웹 대시보드 UI 구현
- [ ] 실시간 업데이트 (WebSocket or Polling)
- [ ] 필터링 및 정렬 기능
- [ ] 분석 상세 페이지

### Phase 3: 고도화 (지속)
- [ ] 팩트체크 자동화 (웹 검색 연동)
- [ ] 알파 점수 정확도 백테스팅
- [ ] 포지션 추적 기능
- [ ] 수익률 대시보드

---

## 7. API 조사 결과

### 7.1 Polymarket API (조사 완료)
- [x] **공식 API 문서**: https://docs.polymarket.com/
- [x] **신규 마켓 조회**: `GET /events` 엔드포인트로 모든 활성 마켓 조회 가능
- [x] **Rate Limit**: 무료 1,000 calls/hour (충분)
- [x] **인증**: 마켓 조회는 **인증 불필요** (트레이딩만 필요)
- [x] **WebSocket**: 실시간 업데이트 지원 (market 채널)
- [x] **필터링**: `closed=false`로 활성 마켓만 조회, 태그/카테고리 필터 가능

**주요 엔드포인트:**
| 엔드포인트 | 용도 |
|------------|------|
| `GET /events` | 모든 이벤트(마켓 그룹) 조회 |
| `GET /markets` | 개별 마켓 조회, 필터링 |
| `GET /tags` | 카테고리/태그 목록 |
| `WSS /market` | 실시간 가격 업데이트 |

### 7.2 Telegram Bot
- [ ] Bot 생성: @BotFather로 생성
- [ ] 메시지 전송: `sendMessage` API
- [ ] Rich format: Markdown 지원, 인라인 버튼 가능

### 7.3 OpenAI API
- [ ] GPT-4o with web search: Responses API 또는 Tavily 연동 필요
- [ ] Function calling: 구조화된 JSON 출력에 활용
- [ ] 예상 비용: 마켓당 ~$0.01-0.05 (프롬프트 크기에 따라)

---

## 8. 리스크 & 고려사항

| 리스크 | 대응 |
|--------|------|
| Polymarket API 변경/차단 | 웹 스크래핑 백업 준비 |
| AI 분석 오류 | 신뢰도 임계값 설정, 수동 검토 옵션 |
| 알림 피로 | 알파 점수 임계값 조정 가능하게 |
| API 비용 | 분석 주기 조절, 캐싱 활용 |
| 법적 이슈 | 개인 용도로만 사용 |

---

## 9. 성공 지표

| 지표 | 목표 |
|------|------|
| 신규 마켓 감지 시간 | < 5분 |
| AI 분석 정확도 | > 70% (백테스트) |
| 알파 기회 발견 | 월 5건 이상 |
| 실제 수익률 | 양수 유지 |

---

## 10. 다음 단계

1. **Polymarket API 조사** - 공식 API 문서 및 사용 가능한 엔드포인트 파악
2. **기술 스택 확정** - Python + FastAPI + SQLite로 시작
3. **MVP 개발 시작** - 크롤러 → AI 분석 → 텔레그램 알림 순서로 구현
