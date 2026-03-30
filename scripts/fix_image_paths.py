import os
import json
import shutil

# Rename folder
old_path = os.path.join('static', 'ABC upload')
new_path = os.path.join('static', 'abc_upload')

if os.path.exists(old_path):
    shutil.move(old_path, new_path)
    print(f'Renamed folder from "{old_path}" to "{new_path}"')

# Update shop.json image paths
with open('content/shop.json', 'r', encoding='utf-8') as f:
    shop = json.load(f)

updated = 0
for pid, prod in shop.items():
    # Update image_path
    if 'image_path' in prod and 'ABC upload' in prod['image_path']:
        prod['image_path'] = prod['image_path'].replace('ABC upload', 'abc_upload')
        updated += 1
    # Update images array
    if 'images' in prod:
        for img in prod['images']:
            if 'image_path' in img and 'ABC upload' in img['image_path']:
                img['image_path'] = img['image_path'].replace('ABC upload', 'abc_upload')
                updated += 1

with open('content/shop.json', 'w', encoding='utf-8') as f:
    json.dump(shop, f, indent=4, ensure_ascii=False)

print(f'Updated {updated} image paths in shop.json')
