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
    old = json.load(f)

folders = [d for d in os.listdir(ABC) if os.path.isdir(os.path.join(ABC,d))]
folder_tokens = {f: tokens(f) for f in folders}

# map old products to folders where possible (ensure unique old pid per folder)
old_map = {pid: prod for pid, prod in old.items()}
assigned = {}
used_old = set()

for f in folders:
    f_toks = folder_tokens[f]
    # collect candidate old pids with scores
    candidates = []
    for pid, prod in old_map.items():
        score = len(f_toks & tokens(prod.get('name','')))
        candidates.append((score, pid))
    # sort by score desc
    candidates.sort(reverse=True)
    best_pid = None
    for score, pid in candidates:
        if score <= 0:
            break
        if pid not in used_old:
            best_pid = pid
            break

    # Try GSM match if no candidate found
    if not best_pid:
        for pid, prod in old_map.items():
            if pid in used_old:
                continue
            for d in prod.get('product_details', []):
                m = re.search(r'(\d+)\s*GSM', d)
                if m and m.group(1) in f:
                    best_pid = pid
                    break
            if best_pid:
                break

    if best_pid:
        assigned[f] = best_pid
        used_old.add(best_pid)
    else:
        assigned[f] = None

# Build new products dict
new = {}
# start id from 1
next_id = 1
# reuse old pids for matched
for f in folders:
    pid = assigned[f]
    if pid is None:
        # find next available numeric id string
        while True:
            key = f"{next_id:06d}"[3:]
            # use same formatting as existing (6? original used 6-digit?). Original used 6 digits? keep 6-digit? We'll use 6-digit trimmed to 6? Simpler: use 6-digit and take last 6. But existing keys like '000001' length 6.
            key = f"{next_id:06d}"
            if key not in new and key not in old_map:
                pid = key
                next_id += 1
                break
            next_id += 1
    else:
        pid = pid

    # get base data from matched old if exists
    base = old_map.get(pid, {}) if pid in old_map else {}
    prod = {}
    prod['name'] = f
    # preserve category, desc, product_details etc from base if present
    for k in ['category','keywords','desc','description','price','Sizes','extended_sizes','extended_moq','image_alt','decorations','delivery_time','instructions','discount','colors_available','custom_color','product_details','moq']:
        if k in base:
            prod[k] = base[k]
    # populate images from ABC folder
    prod_folder = os.path.join(ABC, f)
    color_dirs = [d for d in os.listdir(prod_folder) if os.path.isdir(os.path.join(prod_folder,d))]
    images = []
    main_img = None
    for color in sorted(color_dirs):
        color_path = os.path.join(prod_folder, color)
        files = [fn for fn in os.listdir(color_path) if fn.lower().endswith(('.png','.jpg','.jpeg'))]
        if not files:
            continue
        # pick best file
        chosen = None
        for fn in files:
            if normalize(color).replace(' ','') in fn.lower().replace(' ',''):
                chosen = fn
                break
        if not chosen:
            chosen = files[0]
        rel_path = os.path.join('ABC upload', f, color, chosen).replace('\\','/')
        images.append({'image_path': rel_path, 'image_alt': prod.get('image_alt', f), 'color': color})
        if not main_img:
            main_img = rel_path
    if images:
        prod['images'] = images
    if main_img:
        prod['image_path'] = main_img
    else:
        # keep existing image_path if any
        if 'image_path' in base:
            prod['image_path'] = base['image_path']
    new[pid] = prod

# Write new shop.json
with open(SHOP_JSON, 'w', encoding='utf-8') as f:
    json.dump(new, f, indent=4, ensure_ascii=False)

print('Rebuilt shop.json with', len(new), 'products (one per ABC upload folder)')
