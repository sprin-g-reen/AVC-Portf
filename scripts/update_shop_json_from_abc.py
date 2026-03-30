import os
import json
import re

ROOT = os.path.dirname(os.path.dirname(__file__))
ABC = os.path.join(ROOT, 'static', 'ABC upload')
SHOP_JSON = os.path.join(ROOT, 'content', 'shop.json')

def normalize(s):
    return re.sub(r'[^a-z0-9]+',' ', s.lower()).strip()

def tokens(s):
    return set([t for t in normalize(s).split() if len(t)>2])

with open(SHOP_JSON, 'r', encoding='utf-8') as f:
    shop = json.load(f)

# list product folders
folders = [d for d in os.listdir(ABC) if os.path.isdir(os.path.join(ABC,d))]
folder_tokens = {f: tokens(f) for f in folders}

for pid, prod in shop.items():
    name = prod.get('name','')
    name_tokens = tokens(name)
    best = None
    best_score = 0
    for f, toks in folder_tokens.items():
        score = len(name_tokens & toks)
        if score > best_score:
            best_score = score
            best = f
    # fallback: try matching GSM number
    if not best or best_score==0:
        gsm = ''
        for d in prod.get('product_details',[]):
            m = re.search(r'(\d+)\s*GSM', d)
            if m:
                gsm = m.group(1)
                break
        if gsm:
            for f in folders:
                if gsm in f:
                    best = f
                    break
    if not best:
        # leave images unchanged
        continue

    prod_folder = os.path.join(ABC, best)
    color_dirs = [d for d in os.listdir(prod_folder) if os.path.isdir(os.path.join(prod_folder,d))]
    images = []
    main_img = None
    for color in sorted(color_dirs):
        color_path = os.path.join(prod_folder, color)
        files = [fn for fn in os.listdir(color_path) if fn.lower().endswith(('.png','.jpg','.jpeg'))]
        if not files:
            continue
        # prefer a file that matches color name
        chosen = None
        for fn in files:
            if normalize(color).replace(' ','') in fn.lower().replace(' ',''):
                chosen = fn
                break
        if not chosen:
            # pick a file named exactly like color (case-insensitive)
            for fn in files:
                if os.path.splitext(fn)[0].lower() == normalize(color).replace(' ',''):
                    chosen = fn
                    break
        if not chosen:
            chosen = files[0]
        rel_path = os.path.join('ABC upload', best, color, chosen).replace('\\','/')
        images.append({
            'image_path': rel_path,
            'image_alt': prod.get('image_alt', prod.get('name','')),
            'color': color
        })
        if not main_img:
            main_img = rel_path
    if images:
        prod['images'] = images
    if main_img:
        prod['image_path'] = main_img

with open(SHOP_JSON, 'w', encoding='utf-8') as f:
    json.dump(shop, f, indent=4, ensure_ascii=False)

print('Updated', SHOP_JSON)
