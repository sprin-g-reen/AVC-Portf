import mimetypes
import os
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]


def load_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def upload_image(base_url, token, file_path):
    mime = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    headers = {"Authorization": f"Bearer {token}"}
    with open(file_path, "rb") as fh:
        files = {"files": (file_path.name, fh, mime)}
        resp = requests.post(f"{base_url}/api/upload", headers=headers, files=files, timeout=90)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed for {file_path.name}: {resp.status_code} {resp.text[:180]}")
    return resp.json()[0]["id"]


def main():
    load_env()
    base_url = os.getenv("STRAPI_URL", "").strip().rstrip("/")
    token = os.getenv("STRAPI_API_TOKEN", "").strip()
    collection = os.getenv("STRAPI_HOME_COLLECTION", "homepages").strip("/") or "homepages"

    if not base_url:
        raise SystemExit("Missing STRAPI_URL")
    if not token:
        raise SystemExit("Missing STRAPI_API_TOKEN")

    headers = {"Authorization": f"Bearer {token}"}
    list_resp = requests.get(
        f"{base_url}/api/{collection}",
        headers=headers,
        params={"pagination[pageSize]": 1, "populate": "*"},
        timeout=20,
    )
    if list_resp.status_code != 200:
        raise RuntimeError(f"List failed: {list_resp.status_code} {list_resp.text[:220]}")

    rows = list_resp.json().get("data", [])
    existing = rows[0] if rows else None
    key = (existing or {}).get("documentId") or (existing or {}).get("id")
    allowed_fields = set((existing or {}).keys()) if existing else set()
    blocked = {"id", "documentId", "createdAt", "updatedAt", "publishedAt"}
    allowed_fields = {k for k in allowed_fields if k not in blocked}

    hero_paths = [ROOT / "static" / "hero_mac" / "1.png", ROOT / "static" / "hero_mac" / "2.png", ROOT / "static" / "hero_mac" / "3.png"]
    hero_ids = [upload_image(base_url, token, p) for p in hero_paths if p.exists()]

    data = {
        "hero_images": hero_ids,
        "hero_subtitle": "Perfect for Summer Evenings",
        "hero_title": "Casual and Stylish for All Seasons",
        "hero_price_text": "Starting From",
        "hero_price_value": "$129",
        "hero_cta_text": "SHOP NOW",
        "hero_cta_link": "/shop",
        "exclusive_offer_subtitle": "Services",
        "exclusive_offer_title": "Discover Our Exclusive Offerings",
        "exclusive_offer_cta_text": "Make a enquiry",
        "exclusive_offer_cta_link": "#",
        "service_1_title": "White Label Clothing",
        "service_1_description": "Just starting out? Select from our catalogue of products, add your branding and you're good to go. A great solution for small businesses & startup clothing brands.",
        "service_1_image": "/static/services/1.svg",
        "service_2_title": "Custom Clothing Manufacturing",
        "service_2_description": "Looking for something unique? With our expert guidance, you can design fully custom products, selecting everything from fabrics and sizing to adding your own creative twist. We'll support you every step of the way.",
        "service_2_image": "/static/services/2.svg",
        "service_3_title": "Garment Design Services",
        "service_3_description": "Need assistance with bringing your ideas to life? We cover everything from start to finish and help businesses with their brand development.",
        "service_3_image": "/static/services/3.svg",
    }
    if allowed_fields:
        filtered = {k: v for k, v in data.items() if k in allowed_fields}
    else:
        filtered = data
    payload = {"data": filtered}
    json_headers = {**headers, "Content-Type": "application/json"}

    if key:
        resp = requests.put(f"{base_url}/api/{collection}/{key}", headers=json_headers, json=payload, timeout=30)
    else:
        resp = requests.post(f"{base_url}/api/{collection}", headers=json_headers, json=payload, timeout=30)

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Upsert failed: {resp.status_code} {resp.text[:300]}")

    print("Homepage seed complete.")


if __name__ == "__main__":
    main()
