# Mm.pro - Polymarket 한글화 커뮤니티 서비스

## 프로젝트 개요

Polymarket을 완전 한글화하여 한국 온체인 유저 커뮤니티를 구축하는 서비스.

### 타겟 유저
1. **기존 스포츠 베팅 유저**: 한국에서 불법 도박(스포츠)을 하던 사람들
2. **온체인 네이티브**: 이미 크립토/DeFi 활용에 익숙한 사람들

### 핵심 가치
- Polymarket의 예측 시장을 한국어로 쉽게 접근
- 커뮤니티 기반의 정보 공유 및 소셜 기능
- 빠른 뉴스/이벤트 정보 제공

---

## MVP 기능 목록

### Phase 1 - Core (MVP 필수)

#### 1. 마켓 한글화 뷰
- [ ] Polymarket 마켓 목록 조회 (Gamma API)
- [ ] 마켓 제목/설명 한글 번역 (수동 또는 자동)
- [ ] 실시간 가격 표시 (CLOB API)
- [ ] 마켓 상세 페이지

#### 2. 주요 일정 캘린더
- [ ] 베팅에 영향을 주는 주요 이벤트 일정 표시
- [ ] 예: 미국 대선, FOMC 회의, 스포츠 경기, 코인 이벤트 등
- [ ] 일정별 관련 마켓 연결

#### 3. 한국인 관심 토픽 큐레이션
- [ ] 에디터가 수동으로 픽한 마켓 상단 노출
- [ ] 카테고리: 정치, 스포츠, 크립토, 경제, 연예/문화
- [ ] "오늘의 픽", "주간 핫 마켓" 등 큐레이션 섹션

#### 4. 브레이킹 뉴스 피드
- [ ] 마켓에 영향을 주는 속보 상단 정렬
- [ ] 뉴스 ↔ 관련 마켓 연결
- [ ] 푸시 알림 (선택)

#### 5. 커뮤니티 (토스 주식 스타일)
- [ ] 마켓별 댓글/토론 기능
- [ ] 유저 프로필 (닉네임, 승률, 수익률)
- [ ] 인기 의견 상단 노출
- [ ] 좋아요/싫어요 투표

---

## 기술 스택 (예정)

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **UI**: Tailwind CSS + shadcn/ui
- **상태관리**: Zustand 또는 React Query

### Backend
- **API**: Next.js API Routes 또는 별도 서버
- **DB**: Supabase (PostgreSQL + Auth + Realtime)
- **캐싱**: Redis (가격 데이터 캐싱)

### External APIs
- **Polymarket Gamma API**: 마켓/이벤트 메타데이터
- **Polymarket CLOB API**: 가격, 오더북
- **번역**: DeepL API 또는 GPT API (자동 번역 시)

---

## Polymarket API 참고

### 주요 엔드포인트

```
# 마켓 데이터 (인증 불필요)
GET https://gamma-api.polymarket.com/events      # 이벤트 목록
GET https://gamma-api.polymarket.com/markets     # 마켓 목록
GET https://clob.polymarket.com/price            # 현재 가격
GET https://clob.polymarket.com/book             # 오더북

# 실시간 데이터
WSS wss://ws-subscriptions-clob.polymarket.com/ws/  # 가격 스트림
```

### 데이터 구조
```
Event (이벤트: "2025 미국 대선 승자는?")
  └── Market (마켓: "트럼프 당선")
        ├── Yes 토큰 (가격: $0.65 = 65% 확률)
        └── No 토큰 (가격: $0.35 = 35% 확률)
```

---

## 아이디어 메모

### 차별화 포인트
- 한국어 완전 지원 (UI + 콘텐츠)
- 한국 시간대 기준 일정 표시
- 한국인 관심사 중심 큐레이션
- 커뮤니티 기반 집단지성

### 추후 고려 기능
- [ ] 온체인 지갑 연동 (실제 베팅)
- [ ] 모의 베팅 기능 (법적 리스크 회피)
- [ ] 리더보드 / 랭킹 시스템
- [ ] AI 기반 마켓 분석
- [ ] 텔레그램 봇 연동

### 법적 고려사항
- 한국 도박법 관련 검토 필요
- 정보 제공 vs 베팅 중개의 경계
- 이용약관 및 면책조항

---

## 개발 우선순위

1. **Week 1-2**: 마켓 리스트 + 가격 표시 (읽기 전용)
2. **Week 3-4**: 캘린더 + 큐레이션 시스템
3. **Week 5-6**: 커뮤니티 기능 (댓글, 프로필)
4. **Week 7+**: 뉴스 피드, 알림, 폴리싱

---

## 폴더 구조 (예정)

```
mm-pro/
├── app/                    # Next.js App Router
│   ├── page.tsx           # 메인 (마켓 리스트)
│   ├── market/[id]/       # 마켓 상세
│   ├── calendar/          # 일정 캘린더
│   └── api/               # API Routes
├── components/            # UI 컴포넌트
├── lib/
│   ├── polymarket/        # Polymarket API 클라이언트
│   └── supabase/          # DB 클라이언트
├── types/                 # TypeScript 타입
└── CLAUDE.md              # 이 파일
```

---

## 참고 링크

- [Polymarket 공식 문서](https://docs.polymarket.com/)
- [Polymarket Gamma API](https://gamma-api.polymarket.com)
- [토스 주식 커뮤니티 참고](https://tossinvest.com/)
