import mimetypes
import os
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ABC_ROOT = PROJECT_ROOT / "static" / "abc_upload"


def load_env(path=PROJECT_ROOT / ".env"):
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def upload_media(base_url, token, file_path):
    mime = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    headers = {"Authorization": f"Bearer {token}"}
    with open(file_path, "rb") as fh:
        files = {"files": (file_path.name, fh, mime)}
        resp = requests.post(f"{base_url}/api/upload", headers=headers, files=files, timeout=120)
    if resp.status_code not in (200, 201):
        return None, f"upload failed ({resp.status_code})"
    data = resp.json()
    if not data:
        return None, "upload returned empty data"
    return data[0], None


def create_gallery_entry(base_url, collection, token, media_id, title, sort_order, color):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payloads = [
        {"data": {"image": media_id, "title": title, "sort_order": sort_order, "color": color}},
        {"data": {"image": media_id, "title": title, "sort_order": sort_order}},
        {"data": {"image": media_id, "title": title}},
        {"data": {"image": media_id}},
    ]

    last_error = "unknown"
    for payload in payloads:
        resp = requests.post(
            f"{base_url}/api/{collection}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            return True, None
        last_error = f"{resp.status_code}: {resp.text[:220]}"
        # If this attempt failed due to unsupported key, retry with smaller payload.
        if resp.status_code != 400:
            break

    return False, last_error


def list_existing_gallery_urls(base_url, collection, token):
    headers = {"Authorization": f"Bearer {token}"}
    page = 1
    page_size = 100
    urls = set()

    while True:
        params = {
            "pagination[page]": page,
            "pagination[pageSize]": page_size,
            "populate": "*",
        }
        resp = requests.get(f"{base_url}/api/{collection}", headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            return urls
        payload = resp.json()
        data = payload.get("data", [])
        if not isinstance(data, list):
            break

        for row in data:
            image = row.get("image")
            if isinstance(image, dict):
                url = image.get("url")
                if url:
                    urls.add(str(url))
            elif isinstance(image, list):
                for img in image:
                    if isinstance(img, dict):
                        url = img.get("url")
                        if url:
                            urls.add(str(url))

        meta = payload.get("meta", {}).get("pagination", {})
        page_count = meta.get("pageCount")
        if page_count is not None and page >= page_count:
            break
        if len(data) < page_size:
            break
        page += 1

    return urls


def iter_local_images():
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    for root, _, files in os.walk(ABC_ROOT):
        root_path = Path(root)
        color = root_path.name
        for name in sorted(files):
            ext = Path(name).suffix.lower()
            if ext not in allowed:
                continue
            file_path = root_path / name
            rel = file_path.relative_to(PROJECT_ROOT).as_posix()
            title = f"{root_path.parent.name} - {color} - {name}"
            yield rel, file_path, title, color


def main():
    load_env()

    base_url = os.getenv("STRAPI_URL", "").strip().rstrip("/")
    token = os.getenv("STRAPI_API_TOKEN", "").strip()
    collection = os.getenv("STRAPI_GALLERY_COLLECTION", "galleries").strip("/") or "galleries"

    if not base_url:
        raise SystemExit("Missing STRAPI_URL in .env")
    if not token:
        raise SystemExit("Missing STRAPI_API_TOKEN in .env")
    if not ABC_ROOT.exists():
        raise SystemExit(f"Missing folder: {ABC_ROOT}")

    existing_urls = list_existing_gallery_urls(base_url, collection, token)

    uploaded = 0
    created = 0
    skipped = 0
    failed = 0
    sort_order = 1
    errors = []

    processed = 0
    for rel, file_path, title, color in iter_local_images():
        processed += 1
        # Avoid duplicate entries by file name URL suffix if already present.
        possible_suffix = f"/{file_path.name}"
        if any(url.endswith(possible_suffix) for url in existing_urls):
            skipped += 1
            if processed % 25 == 0:
                print(
                    f"progress processed={processed} uploaded={uploaded} created={created} "
                    f"skipped={skipped} failed={failed}",
                    flush=True,
                )
            continue

        media, upload_err = upload_media(base_url, token, file_path)
        if upload_err:
            failed += 1
            errors.append((rel, upload_err))
            if processed % 25 == 0:
                print(
                    f"progress processed={processed} uploaded={uploaded} created={created} "
                    f"skipped={skipped} failed={failed}",
                    flush=True,
                )
            continue
        uploaded += 1

        media_id = media.get("id")
        media_url = media.get("url", "")
        ok, create_err = create_gallery_entry(base_url, collection, token, media_id, title, sort_order, color)
        if not ok:
            failed += 1
            errors.append((rel, f"create failed: {create_err}"))
            continue

        created += 1
        if media_url:
            existing_urls.add(str(media_url))
        sort_order += 1
        if processed % 25 == 0:
            print(
                f"progress processed={processed} uploaded={uploaded} created={created} "
                f"skipped={skipped} failed={failed}",
                flush=True,
            )

    print(
        f"Gallery import complete. uploaded={uploaded} created={created} skipped={skipped} failed={failed}"
    )
    if errors:
        print("Sample errors:")
        for err in errors[:10]:
            print(err)


if __name__ == "__main__":
    main()
