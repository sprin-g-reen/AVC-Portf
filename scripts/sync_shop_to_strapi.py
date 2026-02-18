import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SHOP_JSON_PATH = os.path.join(PROJECT_ROOT, "content", "shop.json")


def http_json(url, method="GET", token="", payload=None):
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url=url, method=method, headers=headers, data=data)
    with urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))


def find_existing_product(strapi_url, collection, token, external_id):
    query = urlencode({"filters[external_id][$eq]": external_id, "pagination[pageSize]": 1})
    url = f"{strapi_url}/api/{collection}?{query}"
    data = http_json(url, token=token).get("data", [])
    if data:
        row = data[0]
        return row.get("documentId") or row.get("id")
    return None


def build_product_payload(product_id, product):
    payload = dict(product)
    # Normalize keys to match Strapi model naming.
    if "Sizes" in payload and "sizes" not in payload:
        payload["sizes"] = payload.pop("Sizes")
    # Keep compatibility for image variants: if Strapi expects `images` and payload has basic entries,
    # preserve as-is; unsupported keys are filtered later.
    payload["external_id"] = product_id
    return {"data": payload}


def as_blocks_text(text):
    return [
        {
            "type": "paragraph",
            "children": [
                {
                    "type": "text",
                    "text": text or "",
                }
            ],
        }
    ]


def get_allowed_fields(strapi_url, collection, token):
    url = f"{strapi_url}/api/{collection}?pagination[pageSize]=1"
    data = http_json(url, token=token).get("data", [])
    if not data:
        return None
    first = data[0]
    if not isinstance(first, dict):
        return None
    blocked = {"id", "documentId", "createdAt", "updatedAt", "publishedAt"}
    return {k for k in first.keys() if k not in blocked}


def filter_payload_fields(payload, allowed_fields):
    if not allowed_fields:
        return payload
    filtered = {}
    for key, value in payload.items():
        if key in allowed_fields:
            filtered[key] = value
    return filtered


def detect_description_mode(strapi_url, collection, token):
    forced = os.getenv("STRAPI_DESCRIPTION_MODE", "").strip().lower()
    if forced in {"text", "blocks"}:
        return forced

    # Probe one existing entry. If text write doesn't persist, use blocks format.
    query = urlencode({"pagination[pageSize]": 1})
    url = f"{strapi_url}/api/{collection}?{query}"
    rows = http_json(url, token=token).get("data", [])
    if not rows:
        return "text"

    row = rows[0]
    row_key = row.get("documentId") or row.get("id")
    if not row_key:
        return "text"

    probe_text = "Description probe for sync"
    put_url = f"{strapi_url}/api/{collection}/{row_key}"

    # Try plain text first.
    try:
        http_json(put_url, method="PUT", token=token, payload={"data": {"description": probe_text}})
        check = http_json(f"{strapi_url}/api/{collection}/{row_key}", token=token).get("data", {})
        if check.get("description") == probe_text:
            return "text"
    except HTTPError:
        pass

    # Try blocks format.
    try:
        http_json(put_url, method="PUT", token=token, payload={"data": {"description": as_blocks_text(probe_text)}})
        check = http_json(f"{strapi_url}/api/{collection}/{row_key}", token=token).get("data", {})
        if isinstance(check.get("description"), list):
            return "blocks"
    except HTTPError:
        pass

    return "text"


def main():
    strapi_url = os.getenv("STRAPI_URL", "").strip().rstrip("/")
    token = os.getenv("STRAPI_API_TOKEN", "").strip()
    collection = os.getenv("STRAPI_PRODUCTS_COLLECTION", "products").strip("/")

    if not strapi_url:
        raise SystemExit("Missing STRAPI_URL environment variable.")
    if not token:
        raise SystemExit("Missing STRAPI_API_TOKEN environment variable.")

    with open(SHOP_JSON_PATH, "r", encoding="utf-8") as f:
        shop_data = json.load(f)

    created = 0
    updated = 0
    failed = 0
    allowed_fields = get_allowed_fields(strapi_url, collection, token)
    description_mode = detect_description_mode(strapi_url, collection, token)

    for product_id, product in shop_data.items():
        payload = build_product_payload(product_id, product)
        if "description" in payload["data"]:
            raw_desc = payload["data"].get("description") or payload["data"].get("desc") or ""
            if description_mode == "blocks":
                payload["data"]["description"] = as_blocks_text(str(raw_desc))
            else:
                payload["data"]["description"] = str(raw_desc)
        payload["data"] = filter_payload_fields(payload["data"], allowed_fields)
        try:
            existing_key = find_existing_product(strapi_url, collection, token, product_id)
            if existing_key:
                url = f"{strapi_url}/api/{collection}/{existing_key}"
                http_json(url, method="PUT", token=token, payload=payload)
                updated += 1
            else:
                url = f"{strapi_url}/api/{collection}"
                http_json(url, method="POST", token=token, payload=payload)
                created += 1
        except HTTPError as exc:
            failed += 1
            print(f"Failed for product {product_id}: {exc}")

    print(f"Sync complete. created={created}, updated={updated}, failed={failed}")


if __name__ == "__main__":
    main()
