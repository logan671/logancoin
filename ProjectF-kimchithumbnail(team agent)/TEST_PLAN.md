# 김치 썸네일 메이커 - 테스트 계획 (Subagent 버전)

## 테스트 목표
Subagent 구조의 각 컴포넌트가 동작하는지 검증

```
[큐레이터 Subagent] → [이미지 수집 함수] → [썸네일 생성 함수]
     (Claude)           (Serper+rembg)       (RenderForm)
```

---

## 테스트 순서 요약

| Step | 테스트 대상 | AI 필요 | 예상 시간 |
|------|------------|--------|----------|
| 1 | Serper (이미지 검색) | X | 10분 |
| 2 | rembg (누끼 따기) | X | 15분 |
| 3 | RenderForm (썸네일) | X | 20분 |
| 4 | 함수 체인 통합 | X | 10분 |
| 5 | 큐레이터 Subagent | O | 20분 |
| 6 | 전체 E2E 테스트 | O | 15분 |

**총 예상: 1.5시간**

---

## Step 1: Serper API - 이미지 검색

### 준비
- [ ] Serper 가입: https://serper.dev
- [ ] API 키 발급 (2,500회 무료)

### 테스트

```bash
# 터미널에서 실행
curl -X POST 'https://google.serper.dev/images' \
  -H 'X-API-KEY: YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"q": "Donald Trump", "num": 5}'
```

### 예상 결과
```json
{
  "images": [
    {
      "title": "Donald Trump",
      "imageUrl": "https://upload.wikimedia.org/...",
      "source": "wikipedia.org"
    }
  ]
}
```

### 체크리스트
- [ ] API 키 정상 작동
- [ ] 이미지 URL 반환됨
- [ ] 이미지 URL 접근 가능 (브라우저에서 열림)

---

## Step 2: rembg - 누끼 따기

### 준비
- [ ] Python 3.8+ 설치 확인
- [ ] 가상환경 생성 (선택)

```bash
cd /Users/hwlee/Desktop/기본/codefolder/claudecode/ProjectF-kimchithumbnail\(team\ agent\)

# 가상환경 생성 (선택)
python3 -m venv venv
source venv/bin/activate

# 패키지 설치
pip install rembg pillow requests
```

### 테스트 코드

```python
# test_rembg.py
from rembg import remove
from PIL import Image
import requests
from io import BytesIO

# Step 1에서 얻은 이미지 URL (또는 아무 인물 사진)
IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/5/56/Donald_Trump_official_portrait.jpg"

print("1. 이미지 다운로드 중...")
response = requests.get(IMAGE_URL)
input_image = Image.open(BytesIO(response.content))
print(f"   원본 크기: {input_image.size}")

print("2. 누끼 따는 중... (처음엔 모델 다운로드로 오래 걸림)")
output_image = remove(input_image)

print("3. 저장 중...")
output_image.save("test_nobg.png")
print("   완료! test_nobg.png 확인하세요")
```

```bash
python test_rembg.py
```

### 체크리스트
- [ ] rembg 설치 성공
- [ ] 이미지 다운로드 성공
- [ ] 누끼 따기 성공 (test_nobg.png 생성)
- [ ] 배경이 투명하게 제거됨
- [ ] 처리 시간 확인 (예상: 2~10초)

---

## Step 3: RenderForm - 썸네일 생성

### 준비
- [ ] RenderForm 가입: https://renderform.io
- [ ] API 키 발급 (50개 무료)
- [ ] 템플릿 생성

### 템플릿 생성 방법
1. RenderForm 대시보드 → "Create Template"
2. 캔버스 크기: **1200 x 400** (배너형)
3. 요소 추가:
   - 배경: 단색 또는 그라데이션 (고정)
   - 텍스트: `title` 이름으로 추가 (동적)
   - 이미지: `person` 이름으로 추가 (동적)
4. 저장 → **Template ID 복사**

### 테스트

```bash
curl -X POST 'https://get.renderform.io/api/v2/render' \
  -H 'X-API-KEY: YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "template": "YOUR_TEMPLATE_ID",
    "data": {
      "title.text": "트럼프 탄핵될까?",
      "person.src": "https://your-uploaded-image.png"
    }
  }'
```

### 예상 결과
```json
{
  "href": "https://cdn.renderform.io/renders/xxxxx.png",
  "requestId": "abc123"
}
```

### 체크리스트
- [ ] API 키 정상 작동
- [ ] 템플릿 ID 유효
- [ ] 썸네일 이미지 생성됨
- [ ] 텍스트가 제대로 들어감
- [ ] 이미지가 제대로 합성됨
- [ ] 한글 폰트 정상 표시

---

## Step 4: 함수 체인 통합

### 목표
Step 1~3을 하나의 스크립트로 연결

### 테스트 코드

```python
# test_pipeline.py
import requests
from rembg import remove
from PIL import Image
from io import BytesIO
import base64

# API 키 설정
SERPER_API_KEY = "your_serper_key"
RENDERFORM_API_KEY = "your_renderform_key"
TEMPLATE_ID = "your_template_id"

def search_image(query: str) -> str:
    """Serper로 이미지 검색"""
    response = requests.post(
        'https://google.serper.dev/images',
        headers={'X-API-KEY': SERPER_API_KEY},
        json={'q': query, 'num': 5}
    )
    images = response.json().get('images', [])
    return images[0]['imageUrl'] if images else None

def remove_background(image_url: str) -> Image:
    """이미지 다운로드 + 누끼"""
    response = requests.get(image_url)
    input_image = Image.open(BytesIO(response.content))
    return remove(input_image)

def generate_thumbnail(title: str, person_image_url: str) -> str:
    """RenderForm으로 썸네일 생성"""
    response = requests.post(
        'https://get.renderform.io/api/v2/render',
        headers={'X-API-KEY': RENDERFORM_API_KEY},
        json={
            'template': TEMPLATE_ID,
            'data': {
                'title.text': title,
                'person.src': person_image_url
            }
        }
    )
    return response.json().get('href')

# 테스트 실행
if __name__ == "__main__":
    print("=== 김치 썸네일 파이프라인 테스트 ===\n")

    # 1. 이미지 검색
    print("1. 이미지 검색 중...")
    image_url = search_image("Donald Trump")
    print(f"   찾은 이미지: {image_url[:50]}...")

    # 2. 누끼 따기
    print("2. 누끼 따는 중...")
    nobg_image = remove_background(image_url)
    nobg_image.save("pipeline_nobg.png")
    print("   누끼 완료: pipeline_nobg.png")

    # 3. 썸네일 생성 (누끼 이미지를 어딘가 업로드해야 함)
    # TODO: 이미지 호스팅 필요 (S3, Cloudinary 등)
    print("3. 썸네일 생성...")
    print("   ⚠️ 누끼 이미지를 URL로 제공해야 RenderForm에서 사용 가능")
    print("   → 이미지 호스팅 서비스 필요 (다음 단계에서 해결)")

    print("\n=== 테스트 완료 ===")
```

### 이슈: 이미지 호스팅

누끼 딴 이미지를 RenderForm에 전달하려면 **URL이 필요**
→ 이미지 호스팅 서비스 필요

| 옵션 | 장점 | 단점 |
|------|------|------|
| **Cloudinary** | 무료 티어 넉넉, 쉬움 | 가입 필요 |
| **AWS S3** | 안정적 | 설정 복잡 |
| **Supabase Storage** | 기존에 쓰면 통일 | - |
| **imgbb** | 완전 무료, 간단 | 안정성? |

### 체크리스트
- [ ] 전체 파이프라인 연결 성공
- [ ] 이미지 호스팅 방식 결정
- [ ] 에러 핸들링 추가

---

## Step 5: 큐레이터 Subagent 테스트

### 목표
Claude가 폴리마켓 데이터 보고 "한국인 관심도" 판단하는지 확인

### 테스트 방식
Claude Code에서 직접 테스트 (별도 API 호출 없이)

### 테스트 프롬프트

```
다음은 폴리마켓의 활성 마켓 목록입니다.
각 마켓에 대해 "한국인 관심도 점수" (0-100)를 매기고,
상위 5개를 추천해주세요.

마켓 목록:
1. "Will Trump be impeached in 2026?" - 거래량 $2.5M
2. "Bitcoin above $100K by June 2026?" - 거래량 $5.1M
3. "Will BTS have a reunion concert in 2026?" - 거래량 $800K
4. "Fed rate cut in March 2026?" - 거래량 $3.2M
5. "Tesla stock above $500 by Dec 2026?" - 거래량 $1.8M
6. "Samsung overtakes Apple in smartphone sales?" - 거래량 $600K
7. "Will there be a Category 5 hurricane in 2026?" - 거래량 $400K

출력 형식:
{
  "recommendations": [
    {"market": "...", "korea_score": 85, "reason": "..."},
    ...
  ]
}
```

### 체크리스트
- [ ] Claude가 한국 관련 마켓 잘 선별
- [ ] 점수 기준이 합리적
- [ ] JSON 형식으로 출력

---

## Step 6: 전체 E2E 테스트

### 시나리오

```
입력: 관리자가 "트럼프 탄핵" 주제 선택
   ↓
1. 이미지 검색 (Serper)
   ↓
2. 누끼 따기 (rembg)
   ↓
3. 이미지 업로드 (Cloudinary/S3)
   ↓
4. 썸네일 생성 (RenderForm)
   ↓
출력: 완성된 썸네일 URL
```

### 체크리스트
- [ ] 전체 흐름 10초 이내 완료
- [ ] 에러 발생 시 적절한 처리
- [ ] 결과물 품질 OK

---

## 필요한 계정/API 키 총정리

| 서비스 | URL | 용도 | 무료 티어 |
|--------|-----|------|----------|
| Serper | https://serper.dev | 이미지 검색 | 2,500회 |
| RenderForm | https://renderform.io | 썸네일 생성 | 50개 |
| Cloudinary | https://cloudinary.com | 이미지 호스팅 | 25GB |

---

## 테스트 진행 체크리스트

- [ ] **Step 1**: Serper 가입 & 이미지 검색 테스트
- [ ] **Step 2**: rembg 설치 & 누끼 테스트
- [ ] **Step 3**: RenderForm 가입 & 템플릿 & 렌더 테스트
- [ ] **Step 4**: 함수 체인 통합 + 이미지 호스팅
- [ ] **Step 5**: 큐레이터 Subagent 프롬프트 테스트
- [ ] **Step 6**: 전체 E2E 테스트

---

## 예상 이슈 & 대응

| 이슈 | 대응 |
|------|------|
| Serper 이미지 품질 낮음 | 검색어에 "high quality portrait" 추가 |
| rembg 첫 실행 느림 | 모델 다운로드 때문, 이후엔 빠름 |
| rembg 누끼 품질 낮음 | Remove.bg API로 대체 |
| RenderForm 한글 깨짐 | 커스텀 폰트 업로드 |
| 이미지 URL 필요 | Cloudinary 무료 플랜 사용 |
