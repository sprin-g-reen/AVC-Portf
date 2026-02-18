import json
import mimetypes
import os
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHOP_JSON_PATH = PROJECT_ROOT / "content" / "shop.json"


def load_env(path=PROJECT_ROOT / ".env"):
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def load_shop_data():
    with SHOP_JSON_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def upload_file(base_url, token, file_path):
    mime = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    headers = {"Authorization": f"Bearer {token}"}
    with open(file_path, "rb") as fh:
        files = {"files": (file_path.name, fh, mime)}
        resp = requests.post(f"{base_url}/api/upload", headers=headers, files=files, timeout=90)
    if resp.status_code not in (200, 201):
        return None, f"upload failed ({resp.status_code}): {resp.text[:250]}"
    data = resp.json()
    if not data:
        return None, "upload failed: empty response"
    return data[0]["id"], None


def fetch_product(base_url, collection, token, external_id):
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "filters[external_id][$eq]": external_id,
        "pagination[pageSize]": 1,
    }
    resp = requests.get(f"{base_url}/api/{collection}", headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        return None, f"lookup failed ({resp.status_code}): {resp.text[:250]}"
    data = resp.json().get("data", [])
    if not data:
        return None, "entry not found"
    row = data[0]
    return row.get("documentId") or row.get("id"), None


def update_product_images(base_url, collection, token, doc_key, image_items):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"data": {"images": image_items}}
    resp = requests.put(f"{base_url}/api/{collection}/{doc_key}", headers=headers, json=payload, timeout=45)
    if resp.status_code not in (200, 201):
        return f"update failed ({resp.status_code}): {resp.text[:250]}"
    return None


def main():
    load_env()

    base_url = os.getenv("STRAPI_URL", "").strip().rstrip("/")
    token = os.getenv("STRAPI_API_TOKEN", "").strip()
    collection = os.getenv("STRAPI_PRODUCTS_COLLECTION", "products").strip("/")

    if not base_url:
        raise SystemExit("Missing STRAPI_URL")
    if not token:
        raise SystemExit("Missing STRAPI_API_TOKEN")
    if not collection:
        collection = "products"

    shop_data = load_shop_data()

    product_ok = 0
    product_failed = 0
    total_colors_uploaded = 0
    errors = []

    for external_id, product in shop_data.items():
        doc_key, err = fetch_product(base_url, collection, token, external_id)
        if err:
            product_failed += 1
            errors.append((external_id, err))
            continue

        raw_images = product.get("images") or []
        image_items = []

        for img in raw_images:
            rel_path = img.get("image_path")
            if not rel_path:
                continue
            file_path = PROJECT_ROOT / "static" / rel_path
            if not file_path.is_file():
                continue

            media_id, upload_err = upload_file(base_url, token, file_path)
            if upload_err:
                errors.append((external_id, upload_err))
                continue

            image_items.append(
                {
                    "color": str(img.get("color", "default")),
                    "image_alt": str(img.get("image_alt", product.get("name", "Product"))),
                    "image": media_id,
                }
            )
            total_colors_uploaded += 1

        update_err = update_product_images(base_url, collection, token, doc_key, image_items)
        if update_err:
            product_failed += 1
            errors.append((external_id, update_err))
            continue

        product_ok += 1

    print(
        f"Color image sync complete. products_ok={product_ok} products_failed={product_failed} "
        f"color_images_uploaded={total_colors_uploaded}"
    )
    if errors:
        print("Sample errors:")
        for item in errors[:10]:
            print(item)


if __name__ == "__main__":
    main()
