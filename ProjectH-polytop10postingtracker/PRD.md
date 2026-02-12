# Polymarket Alpha Daily – PRD v0.4
프로젝트명: Polymarket Alpha Daily (또는 DeSpread PM Alpha Feed)

## 1. 목표
매일 최근 24시간 Polymarket 관련 고퀄 알파 트레이딩 포스트 Top 10을 자동 수집하여  
텍스트 + 이미지 + 링크 포함한 깔끔한 공개 웹페이지로 제공  
(중복 포스트 3일 이내 제외 + 부족 시 11~20위 보충)

## 2. 핵심 기능 (MVP)
- 매일 1회 자동 실행 (KST 오전 9시)
- Grok API 호출 → Polymarket 알파/전략/웨일/copy-trade 관련 Top 10 포스트 수집
- 랭킹 규칙: `rank` 우선, 없으면 `view_count`, 둘 다 없으면 `(like + repost + reply)` 합산 점수
- 중복 제외: 최근 3일간 피처된 `tweet_id` 저장 → 제외 후 부족하면 11~20위에서 보충
- 출력: index.html 파일 생성 (카드 UI, 모바일 반응형)
- 이미지: X 원본 URL 그대로 사용 (lazy loading)
- 번역: Grok로 한국어 번역 생성 후 한국어 본문을 카드 메인으로 노출, 원문은 X 링크로 제공
- 배포: GitHub Actions에서 생성/커밋/푸시 → Vercel 자동 배포
- 배포 안전장치: 변경 없으면 커밋 스킵, 커밋 메시지에 `[skip ci]`, workflow `concurrency`로 중복 실행 방지
- fallback: API 실패 시 이전 index.html 유지
- 잔액/크레딧 부족 감지 시: 웹사이트 상단 경고 배너 노출 (`잔액 충전하세요`)

## 3. 기술 스택 (로컬 개발 기준)
- 언어: Python 3.10+
- 핵심 라이브러리:
  - requests 또는 grok-sdk (xAI 공식)
  - jinja2 (HTML 템플릿)
  - python-dotenv (API 키 관리)
- Git: 이미 연결됨 (main 브랜치 사용 추천)
- 호스팅: Vercel (정적 사이트)
- 스케줄러: GitHub Actions (cron) 또는 로컬 cron + git push 스크립트
- 저장소: 간단 json 파일로 이전 `tweet_id` 로그 (db는 MVP에선 불필요)

## 4. 파일 구조 (예시)
project-root/
├── main.py               # 메인 실행 스크립트
├── template.html         # Jinja2 템플릿
├── previous_posts.json   # 중복 방지용 { "date": ["tweet_id1", ...] }
├── .env                  # GROK_API_KEY=xxx
├── requirements.txt
└── public/               # Vercel이 빌드할 폴더 (index.html 생성 위치)

## 5. 성공 기준 (MVP 완료 체크리스트)
- [ ] 매일 새 index.html 생성 확인
- [ ] 중복 포스트 3일 이내(`tweet_id` 기준) 제외 동작 확인
- [ ] 이미지 정상 로드 (브라우저에서)
- [ ] git push 후 Vercel에 즉시 반영
- [ ] 페이지 로드 3초 이내
- [ ] 한국어 번역 본문 + 원문 링크 표시 확인
- [ ] 잔액/크레딧 부족 시 상단 배너 표시 확인

완료 목표: 1~2주 내 MVP 배포
