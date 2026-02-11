# ProjectF - 김치 썸네일 메이커 기획 V2

## 요구사항 재정의 (2026-02-09)

### 핵심 요구사항

**단순 템플릿 채우기가 아닌 "입체적 합성"**

```
❌ 기존 이해 (틀렸음)
   배경 1장 + 인물 누끼 1장 + 텍스트 = 끝

✅ 실제 요구사항
   - 주제에 따라 다양한 이미지 검색 (인물, 배경, 아이콘 등)
   - 여러 레이어가 자연스럽게 어우러진 디자인
   - 뉴스 썸네일 / NANOBANANA 스타일의 퀄리티
```

### 주제 유형별 처리

| 주제 유형 | 예시 | 필요한 이미지 |
|----------|------|--------------|
| 인물 중심 | 트럼프 탄핵? | 인물 사진 + 관련 배경 (백악관 등) |
| 경제 | 한국 GDP? | 차트, 그래프, 한국은행, 원화 |
| 크립토 | BTC $100K? | 비트코인 로고, 차트, 코인 이미지 |
| 스포츠 | 월드컵 우승? | 경기장, 트로피, 국기 |
| 기업 | 애플 발표? | 로고, 제품, 행사장 |

### AI가 해야 할 것

```
입력: "한국 26년 1분기 GDP는?"
         ↓
   1. 주제 분석 & 카테고리 분류
         ↓
   2. 이미지 검색 키워드 생성
      - "한국 경제 그래프"
      - "한국은행 건물"
      - "원화 지폐"
         ↓
   3. 디자인 스타일 결정
      - 레이아웃: "chart_overlay"
      - 색상 무드: "blue_professional"
         ↓
   4. 이미지 검색 & 선택
         ↓
   5. 입체적 합성
         ↓
출력: 완성된 썸네일
```

---

## 기술 대안 비교

### 대안 1: RenderForm (기존안)

```
장점:
- 이미 테스트 완료
- 사용 쉬움

단점:
- 템플릿 고정 → 유연성 부족
- 주제별로 다른 템플릿 필요 (수십 개?)
- "입체적 합성" 한계
- 월 비용 발생 ($9~$14)

결론: ❌ 요구사항에 부적합
```

### 대안 2: HTML/CSS + Puppeteer (자체 구현)

```
장점:
- 완전한 자유도
- 코드로 레이어 구조 제어
- 주제별 다른 레이아웃 동적 생성
- 비용 없음 (자체 서버)
- 입체적 합성 가능

단점:
- 디자인 템플릿 직접 만들어야 함
- 개발 시간 더 필요

결론: ✅ 적합
```

### 대안 3: AI 이미지 생성 (DALL-E, Midjourney)

```
장점:
- 가장 창의적
- 매번 새로운 이미지
- NANOBANANA 스타일 가능

단점:
- DALL-E: 실제 인물 생성 거부
- Midjourney: API 없음 (자동화 어려움)
- 일관성 유지 어려움
- 비용 높음

결론: ⚠️ 단독으로는 부적합, 보조로는 가능
```

### 대안 4: 하이브리드 (추천)

```
HTML/CSS + Puppeteer (기본)
  +
AI 이미지 생성 (일부 요소)
  +
Serper 이미지 검색 (실사)

장점:
- 실사 인물/배경: Serper 검색
- 아이콘/일러스트: AI 생성 또는 스톡
- 레이아웃/합성: HTML/CSS로 자유롭게
- 가장 유연함

결론: ✅✅ 최적
```

---

## 추천 구조 (V2)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         메인 에이전트                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ Subagent 1  │  │ Subagent 2  │  │ Subagent 3  │  │ Subagent 4│  │
│  │ 분석 & 기획  │  │ 이미지 수집  │  │ 이미지 처리  │  │ 합성/렌더 │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘  │
│         │                │                │                │        │
│         ▼                ▼                ▼                ▼        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ Claude AI   │  │   Serper    │  │   rembg     │  │ Puppeteer │  │
│  │ 주제 분석   │  │ 이미지 검색  │  │   Sharp     │  │   HTML    │  │
│  │ 키워드 생성 │  │ (+ AI생성?) │  │  이미지처리  │  │  렌더링   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Subagent 역할 상세

#### Subagent 1: 분석 & 기획 (Claude)

```json
입력: "트럼프가 2026년까지 탄핵될까?"

출력:
{
  "category": "politics_person",
  "main_subject": "Donald Trump",
  "context": "impeachment",
  "image_plan": {
    "primary": {
      "type": "person",
      "query": "Donald Trump official photo",
      "processing": "remove_background"
    },
    "background": {
      "type": "location",
      "query": "US Capitol building dramatic",
      "processing": "darken_overlay"
    },
    "accent": {
      "type": "icon",
      "query": "gavel justice icon",
      "processing": "none"
    }
  },
  "layout": "person_right_text_left",
  "color_mood": "dark_dramatic",
  "title_ko": "트럼프, 2026년 탄핵될까?"
}
```

#### Subagent 2: 이미지 수집

- Serper로 각 이미지 검색
- 품질/해상도 기준으로 선택
- 다운로드

#### Subagent 3: 이미지 처리

- rembg로 누끼 (필요시)
- Sharp로 리사이징, 색보정
- 오버레이/필터 적용

#### Subagent 4: 합성 & 렌더링

- HTML/CSS 템플릿 동적 생성
- 이미지 + 텍스트 배치
- Puppeteer로 스크린샷 → 최종 이미지

---

## HTML/CSS 템플릿 예시

### 레이아웃 1: 인물 오른쪽 + 텍스트 왼쪽 (파월 스타일)

```html
<div class="thumbnail" style="width:1200px; height:400px; position:relative; overflow:hidden;">
  <!-- 배경 -->
  <div class="bg" style="
    position:absolute; inset:0;
    background: url('{{background}}') center/cover;
  "></div>

  <!-- 어두운 그라데이션 -->
  <div class="overlay" style="
    position:absolute; inset:0;
    background: linear-gradient(90deg, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.3) 100%);
  "></div>

  <!-- 인물 (오른쪽) -->
  <img class="person" src="{{person}}" style="
    position:absolute; right:-50px; bottom:0;
    height:120%; width:auto;
  "/>

  <!-- 텍스트 (왼쪽) -->
  <div class="content" style="
    position:absolute; left:40px; top:40px;
    color:white; font-family:'Pretendard';
  ">
    <h1 style="font-size:42px; font-weight:800;">{{title}}</h1>

    <div class="vote-bar" style="margin-top:40px;">
      <div>{{option1}}</div>
      <div class="bar blue" style="width:{{yes_percent}}%"></div>
      <div>{{option2}}</div>
      <div class="bar red" style="width:{{no_percent}}%"></div>
    </div>
  </div>
</div>
```

### 레이아웃 2: 배경 중심 + 오버레이 (경제/차트)

```html
<div class="thumbnail">
  <!-- 배경 (차트/그래프 이미지) -->
  <div class="bg" style="background: url('{{chart_image}}') center/cover;"></div>

  <!-- 블러 + 어두운 오버레이 -->
  <div class="overlay" style="
    backdrop-filter: blur(3px);
    background: rgba(0,20,40,0.7);
  "></div>

  <!-- 아이콘 -->
  <img class="icon" src="{{icon}}" style="
    position:absolute; right:40px; top:50%;
    transform:translateY(-50%);
    width:150px; opacity:0.8;
  "/>

  <!-- 텍스트 -->
  <h1>{{title}}</h1>
  ...
</div>
```

---

## 변경된 테스트 계획

| Step | 기존 | 변경 |
|------|------|------|
| 1 | Serper 테스트 | ✅ 완료 (유지) |
| 2 | rembg 테스트 | ✅ 완료 (유지) |
| 3 | RenderForm 테스트 | ❌ 제외 |
| 3-new | HTML + Puppeteer 테스트 | 새로 추가 |
| 4 | 통합 테스트 | 수정 필요 |
| 5 | 큐레이터 Subagent | 확장 (이미지 기획까지) |

---

## 다음 단계

1. [ ] HTML/CSS 템플릿 프로토타입 제작
2. [ ] Puppeteer 렌더링 테스트
3. [ ] 분석 Subagent 프롬프트 설계
4. [ ] 전체 파이프라인 통합
5. [ ] 웹 UI 구현

---

## 비용 비교

| 항목 | 기존 (RenderForm) | 변경 (자체 구현) |
|------|------------------|-----------------|
| 이미지 검색 | Serper ~$0.20/월 | Serper ~$0.20/월 |
| 누끼 | rembg 무료 | rembg 무료 |
| 썸네일 생성 | RenderForm $9~14/월 | **무료** (Puppeteer) |
| **총합** | ~$10~15/월 | ~$0.20/월 |
