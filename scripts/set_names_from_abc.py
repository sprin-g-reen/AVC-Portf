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

folders = [d for d in os.listdir(ABC) if os.path.isdir(os.path.join(ABC,d))]
folder_tokens = {f: tokens(f) for f in folders}

changes = []
for pid, prod in shop.items():
    orig_name = prod.get('name','')
    name_tokens = tokens(orig_name)
    best = None
    best_score = 0
    for f, toks in folder_tokens.items():
        score = len(name_tokens & toks)
        if score > best_score:
            best_score = score
            best = f
    # fallback: match GSM in product_details
    if not best or best_score==0:
        gsm = ''
        for d in prod.get('product_details', []):
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
        # try matching by category tokens
        cat = prod.get('category','')
        cat_toks = tokens(cat)
        for f, toks in folder_tokens.items():
            if len(cat_toks & toks) > 0:
                best = f
                break
    if best and shop[pid].get('name') != best:
        shop[pid]['name'] = best
        changes.append((pid, orig_name, best))

if changes:
    with open(SHOP_JSON, 'w', encoding='utf-8') as f:
        json.dump(shop, f, indent=4, ensure_ascii=False)

print('Updated names for', len(changes), 'products')
for c in changes:
    print(c)
