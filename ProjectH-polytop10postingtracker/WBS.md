# Polymarket Alpha Daily – To-Do & 준비물 & 개발 로드맵

## 준비해야 할 자료 / 키값 (지금 당장 확보)
1. Grok API 키
   - https://console.x.ai → 로그인 → API Keys → Create new key
   - .env 파일에 GROK_API_KEY=sk-xxx... 형태로 저장
2. GitHub 리포지토리 (이미 있으면 OK)
   - 새로 만들 경우: polymarket-alpha-daily 또는 despread-pm-alpha
   - Vercel과 연결할 repo
3. Vercel 계정
   - https://vercel.com/signup → GitHub 연동
   - repo import 후 프로젝트 생성 (Static HTML 선택)
4. Python 환경
   - Python 3.10+ 설치 확인
   - pip install requests python-dotenv jinja2

## 단계별 To-Do (순서대로 체크)

### Step 1 – 환경 셋업 (오늘~내일)
- [ ] .env 파일 생성 & GROK_API_KEY 입력
- [ ] requirements.txt 작성

- [ ] pip install -r requirements.txt
- [ ] 간단 테스트 스크립트 작성 → Grok API 호출 성공 확인
(프롬프트 예시: "최근 24시간 Polymarket 알파 트레이딩 top 10 포스트를 JSON으로 반환해")

### Step 2 – 데이터 수집 & 중복 로직 구현 (2~4일)
- [ ] Grok API로 포스트 리스트 가져오기 (JSON 형식)
- [ ] 랭킹 fallback 구현: `rank` 우선, 없으면 `view_count`, 없으면 `(like+repost+reply)` 점수
- [ ] previous_posts.json 로드 → 최근 3일 `tweet_id` 제외 필터
- [ ] 2차 중복(text hash)은 MVP에서 제외 (필요 시 v1.1에서 추가)
- [ ] 부족하면 "11~20위" 쿼리로 추가 호출
- [ ] 결과: 리스트 [{id, text, images[], author, url, summary}] 형태

### Step 3 – 번역 + HTML 생성 (템플릿 + Jinja2) (3~5일)
- [ ] Grok로 영어 원문 → 한국어 번역 생성
- [ ] 카드에는 한국어 번역을 메인으로 표기, 원문은 X 링크 버튼으로 제공
- [ ] template.html 작성 (카드 UI, lazy loading img)
- [ ] main.py에서 Jinja2로 렌더링 → public/index.html 저장
- [ ] 로컬에서 python main.py 실행 → 브라우저로 확인

### Step 4 – 자동화 & 배포 (5~7일)
- [ ] GitHub Actions workflow yaml 작성 (UTC 기준 `0 0 * * *`, 즉 KST 오전 9시)
- checkout → python main.py → git commit & push
- [ ] 안전장치 추가
  - 변경 없으면 커밋 스킵
  - 커밋 메시지에 `[skip ci]` 포함
  - `concurrency` 설정으로 중복 실행 방지
- [ ] Vercel에 프로젝트 연결 → 커스텀 도메인 설정 (옵션)
- [ ] 첫 배포 테스트 → vercel.app URL 확인

### Step 5 – 마무리 & 테스트
- [ ] 2~3일 연속 실행 → 중복 제외 잘 되는지 확인
- [ ] 모바일에서 페이지 보기 테스트
- [ ] 크레딧/잔액 부족 감지 시 상단 배너(`잔액 충전하세요`) 노출 확인
- [ ] X에 링크 공유용 미리보기 이미지 생성 (옵션)

필요할 때마다 물어봐  
- API 호출 샘플 코드
- Jinja2 템플릿 예시
- GitHub Actions yaml 샘플
- 중복 로직 세부 구현 방법

로컬에서 차근차근 해보고, 막히는 부분 나오면 바로 말해줘. 화이팅! 🚀
