import json

with open('content/shop.json', 'r', encoding='utf-8') as f:
    shop = json.load(f)

for pid, prod in shop.items():
    img_path = prod.get('image_path', 'MISSING')
    print(f"{pid}: {img_path}")
