import os
import json

with open('content/shop.json', 'r', encoding='utf-8') as f:
    shop = json.load(f)

missing = []
found = 0

for pid, prod in shop.items():
    img_path = prod.get('image_path', '')
    full_path = os.path.join('static', img_path)
    if not os.path.exists(full_path):
        missing.append(f"{pid}: {full_path}")
    else:
        found += 1
    
    # Check images array
    for img in prod.get('images', []):
        img_path = img.get('image_path', '')
        full_path = os.path.join('static', img_path)
        if not os.path.exists(full_path):
            missing.append(f"{pid} color: {full_path}")

print(f"Found {found} main images")
if missing:
    print(f"Missing {len(missing)} images:")
    for m in missing[:10]:
        print(f"  {m}")
else:
    print("All images exist!")
