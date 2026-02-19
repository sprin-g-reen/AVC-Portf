import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SHOP_JSON_PATH = os.path.join(PROJECT_ROOT, "content", "shop.json")
DEFAULT_PRODUCT_FIELDS = {
    "external_id",
    "name",
    "description",
    "desc",
    "price",
    "category",
    "image_path",
    "image_alt",
    "images",
    "extended_moq",
    "discount",
    "colors_available",
    "custom_color",
    "delivery_time",
    "extended_sizes",
    "sizes",
    "keywords",
    "decorations",
    "instructions",
    "product_details",
}


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
    forced = os.getenv("STRAPI_ALLOWED_PRODUCT_FIELDS", "").strip()
    if forced:
        return {x.strip() for x in forced.split(",") if x.strip()}

    url = f"{strapi_url}/api/{collection}?pagination[pageSize]=1"
    data = http_json(url, token=token).get("data", [])
    if not data:
        # First sync may hit an empty collection; use safe defaults from our schema.
        return set(DEFAULT_PRODUCT_FIELDS)
    first = data[0]
    if not isinstance(first, dict):
        return set(DEFAULT_PRODUCT_FIELDS)
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
            method = "PUT" if existing_key else "POST"
            url = f"{strapi_url}/api/{collection}/{existing_key}" if existing_key else f"{strapi_url}/api/{collection}"

            # Retry loop for "Invalid key <field>" errors on first-time schema mismatches.
            for _ in range(5):
                try:
                    http_json(url, method=method, token=token, payload=payload)
                    if method == "PUT":
                        updated += 1
                    else:
                        created += 1
                    break
                except HTTPError as exc:
                    error_body = ""
                    try:
                        error_body = exc.read().decode("utf-8", errors="replace")
                    except Exception:
                        pass

                    invalid_key = None
                    if error_body:
                        try:
                            parsed = json.loads(error_body)
                            invalid_key = (
                                parsed.get("error", {})
                                .get("details", {})
                                .get("key")
                            )
                        except Exception:
                            invalid_key = None

                    if exc.code == 400 and invalid_key and invalid_key in payload["data"]:
                        payload["data"].pop(invalid_key, None)
                        if isinstance(allowed_fields, set):
                            allowed_fields.discard(invalid_key)
                        continue

                    failed += 1
                    if error_body:
                        print(f"Failed for product {product_id}: {exc} | {error_body}")
                    else:
                        print(f"Failed for product {product_id}: {exc}")
                    break
            else:
                failed += 1
                print(f"Failed for product {product_id}: too many retries")
        except HTTPError as exc:
            failed += 1
            print(f"Failed for product {product_id}: {exc}")

    print(f"Sync complete. created={created}, updated={updated}, failed={failed}")


if __name__ == "__main__":
    main()
