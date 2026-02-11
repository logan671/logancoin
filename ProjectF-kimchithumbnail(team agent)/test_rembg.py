from rembg import remove
from PIL import Image
import requests
from io import BytesIO

# Serper에서 찾은 고해상도 이미지 (History.com)
IMAGE_URL = "https://res.cloudinary.com/aenetworks/image/upload/c_fill,ar_2,w_3840,h_1920,g_auto/dpr_auto/f_auto/q_auto:eco/v1/donald-trump-gettyimages-687193180"

print("1. 이미지 다운로드 중...")
response = requests.get(IMAGE_URL)
print(f"   다운로드 완료: {len(response.content) / 1024:.1f} KB")

input_image = Image.open(BytesIO(response.content))
print(f"   원본 크기: {input_image.size}")

print("2. 누끼 따는 중... (첫 실행 시 모델 다운로드로 오래 걸림)")
output_image = remove(input_image)

print("3. 저장 중...")
output_path = "/Users/hwlee/Desktop/기본/codefolder/claudecode/ProjectF-kimchithumbnail(team agent)/test_nobg.png"
output_image.save(output_path)
print(f"   완료! {output_path}")
