# 김치 썸네일 메이커 - Subagent 구조 설계

## 개요

Agent Team 대신 **Subagent 패턴**으로 구현
- 메인 에이전트가 전체 흐름 관리
- 각 작업을 Subagent에게 위임
- 결과만 받아서 다음 단계로 전달

---

## 전체 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                         메인 에이전트                                 │
│                      (오케스트레이터)                                 │
│                                                                     │
│  역할:                                                              │
│  - 전체 파이프라인 관리                                               │
│  - 관리자 입력 받기 (웹 UI에서)                                       │
│  - Subagent 호출 & 결과 조합                                         │
│  - 최종 결과 저장 & 알림                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│     │ Subagent 1  │  │ Subagent 2  │  │ Subagent 3  │              │
│     │ 큐레이터     │  │ 이미지수집   │  │ 썸네일생성   │              │
│     └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│            │                │                │                      │
│            ▼                ▼                ▼                      │
│     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│     │ Polymarket  │  │   Serper    │  │ RenderForm  │              │
│     │ API 호출    │  │ + rembg     │  │ API 호출    │              │
│     └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Subagent 상세 설계

### Subagent 1: 큐레이터

**호출 시점**:
- 주기적 (예: 1시간마다) 또는 관리자 요청 시

**입력**:
```json
{
  "task": "curate",
  "filters": {
    "min_volume_percentile": 70,
    "categories": ["politics", "crypto", "sports", "entertainment"]
  }
}
```

**역할**:
1. Polymarket API에서 활성 마켓 목록 가져오기
2. 거래량 상위 70% 필터링
3. 각 마켓에 대해 "한국인 관심도" 점수 매기기
4. 상위 N개 추천 목록 반환

**출력**:
```json
{
  "recommendations": [
    {
      "market_id": "abc123",
      "title": "Will Trump be impeached in 2026?",
      "title_ko": "트럼프 2026년 탄핵될까?",
      "volume": 1500000,
      "korea_score": 85,
      "reason": "미국 정치 이슈, 한국 뉴스에서도 자주 다뤄짐",
      "suggested_thumbnail_text": "트럼프 탄핵?",
      "key_person": "Donald Trump"
    },
    ...
  ]
}
```

---

### Subagent 2: 이미지 수집가

**호출 시점**:
- 관리자가 주제 선택 후, 또는 큐레이터 결과 받은 후

**입력**:
```json
{
  "task": "collect_image",
  "query": "Donald Trump",
  "style": "news"  // "news" | "portrait" | "action"
}
```

**역할**:
1. Serper API로 이미지 검색
2. 적절한 이미지 선택 (해상도, 구도 고려)
3. 이미지 다운로드
4. rembg로 누끼 따기
5. 누끼 딴 이미지 URL/파일 반환

**출력**:
```json
{
  "original_url": "https://..../trump.jpg",
  "nobg_url": "https://..../trump_nobg.png",  // 또는 base64
  "source": "nytimes.com",
  "dimensions": "800x600"
}
```

---

### Subagent 3: 썸네일 생성기

**호출 시점**:
- 이미지 수집 완료 후

**입력**:
```json
{
  "task": "generate_thumbnail",
  "template_id": "banner_v1",
  "data": {
    "title": "트럼프 탄핵?",
    "subtitle": "YES 65% / NO 35%",
    "person_image_url": "https://..../trump_nobg.png"
  }
}
```

**역할**:
1. RenderForm API 호출
2. 템플릿에 데이터 채워서 이미지 생성
3. 생성된 이미지 URL 반환

**출력**:
```json
{
  "thumbnail_url": "https://renderform.io/rendered/abc123.png",
  "template_used": "banner_v1",
  "generated_at": "2026-02-09T15:30:00Z"
}
```

---

## 전체 플로우

### 플로우 A: 자동 큐레이션 → 관리자 선택 → 썸네일 생성

```
1. [자동/주기적] 메인 에이전트 → Subagent 1 (큐레이터)
   "폴리마켓에서 한국인 관심 주제 찾아줘"
                    ↓
2. 큐레이터 결과 → 웹 대시보드에 표시
   [트럼프 탄핵] [비트코인 $100K] [테일러 스위프트]
                    ↓
3. 관리자가 "트럼프 탄핵" 클릭
                    ↓
4. 메인 에이전트 → Subagent 2 (이미지 수집)
   "Donald Trump 이미지 검색하고 누끼 따줘"
                    ↓
5. 메인 에이전트 → Subagent 3 (썸네일 생성)
   "이 이미지로 썸네일 만들어줘"
                    ↓
6. 썸네일 대기열에 저장 → 관리자 승인 → 게시
```

### 플로우 B: 관리자 수동 입력 → 썸네일 생성

```
1. 관리자가 직접 입력:
   - 주제: "일론 머스크 DOGE"
   - 인물: "Elon Musk"
                    ↓
2. 메인 에이전트 → Subagent 2 (이미지 수집)
   "Elon Musk 이미지 검색하고 누끼 따줘"
                    ↓
3. 메인 에이전트 → Subagent 3 (썸네일 생성)
   "이 이미지로 썸네일 만들어줘"
                    ↓
4. 썸네일 대기열에 저장 → 관리자 승인 → 게시
```

---

## 기술 구현

### 메인 에이전트 (Next.js API Route)

```typescript
// /api/thumbnail/generate.ts

export async function POST(req: Request) {
  const { topic, person, mode } = await req.json();

  // 1. 이미지 수집 Subagent 호출
  const imageResult = await callSubagent('image-collector', {
    query: person,
    style: 'news'
  });

  // 2. 썸네일 생성 Subagent 호출
  const thumbnailResult = await callSubagent('thumbnail-generator', {
    title: topic,
    person_image_url: imageResult.nobg_url
  });

  // 3. DB에 저장 (대기열)
  await saveToPendingQueue({
    topic,
    thumbnail_url: thumbnailResult.thumbnail_url,
    status: 'pending'
  });

  return { success: true, thumbnail_url: thumbnailResult.thumbnail_url };
}
```

### Subagent 호출 방식

**옵션 A: Claude API로 직접 호출**
```typescript
async function callSubagent(type: string, input: any) {
  const response = await anthropic.messages.create({
    model: 'claude-sonnet-4-20250514',
    system: SUBAGENT_PROMPTS[type],
    messages: [{ role: 'user', content: JSON.stringify(input) }],
    tools: SUBAGENT_TOOLS[type]
  });
  return parseResponse(response);
}
```

**옵션 B: 그냥 함수로 구현 (AI 불필요한 작업)**
```typescript
// 이미지 검색, 누끼, RenderForm 호출은 그냥 함수로
async function collectImage(query: string) {
  const serperResult = await searchImages(query);
  const imageUrl = serperResult.images[0].imageUrl;
  const nobgImage = await removeBackground(imageUrl);
  return nobgImage;
}
```

---

## 권장 구현 방식

| Subagent | AI 필요? | 구현 방식 |
|----------|---------|----------|
| 큐레이터 | **예** | Claude API (한국 관심도 판단) |
| 이미지 수집 | 아니오 | 일반 함수 (Serper + rembg) |
| 썸네일 생성 | 아니오 | 일반 함수 (RenderForm API) |

**결론**:
- 큐레이터만 Claude Subagent로
- 나머지는 그냥 함수 체인으로 구현
- 이게 더 빠르고 저렴함

---

## 파일 구조 (예상)

```
ProjectF-kimchithumbnail/
├── app/
│   ├── page.tsx                 # 관리자 대시보드
│   ├── api/
│   │   ├── curate/route.ts      # 큐레이션 API
│   │   ├── thumbnail/
│   │   │   ├── generate/route.ts # 썸네일 생성
│   │   │   └── approve/route.ts  # 승인 처리
│   │   └── webhook/route.ts      # 외부 훅
├── lib/
│   ├── subagents/
│   │   └── curator.ts           # 큐레이터 Subagent (Claude)
│   ├── services/
│   │   ├── serper.ts            # 이미지 검색
│   │   ├── rembg.ts             # 누끼 따기
│   │   └── renderform.ts        # 썸네일 생성
│   └── polymarket/
│       └── api.ts               # 폴리마켓 API
├── components/
│   ├── CurationList.tsx         # 큐레이션 목록
│   ├── ThumbnailPreview.tsx     # 썸네일 미리보기
│   └── ApprovalQueue.tsx        # 승인 대기열
└── SUBAGENT_ARCHITECTURE.md     # 이 문서
```

---

## 다음 단계

1. [ ] Serper API 테스트
2. [ ] rembg 로컬 테스트
3. [ ] RenderForm 가입 & 템플릿 생성
4. [ ] 큐레이터 Subagent 프롬프트 설계
5. [ ] 웹 대시보드 UI 구현
6. [ ] 전체 통합 테스트
