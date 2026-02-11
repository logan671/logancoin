from rembg import remove
from PIL import Image
import os

IMG_DIR = os.path.join(os.path.dirname(__file__), 'images')

# Images that need background removal
targets = [
    'badbunny_portrait_0.jpg',
    'culinary_person_0.jpg',
    'hottest_earth_0.jpg',
]

for filename in targets:
    filepath = os.path.join(IMG_DIR, filename)
    if not os.path.exists(filepath):
        print(f'Skip (not found): {filename}')
        continue

    print(f'Processing: {filename}...')
    img = Image.open(filepath)
    result = remove(img)

    out_name = os.path.splitext(filename)[0] + '_nobg.png'
    out_path = os.path.join(IMG_DIR, out_name)
    result.save(out_path)
    print(f'  Saved: {out_name}')

print('\nDone!')
