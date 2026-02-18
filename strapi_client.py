import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [value]


def _safe_get(entry, *keys, default=None):
    for key in keys:
        if isinstance(entry, dict) and key in entry:
            return entry[key]
    return default


def _media_url_from_value(value, strapi_url):
    if not value:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        if "url" in value and value["url"]:
            url = str(value["url"])
            if url.startswith("http://") or url.startswith("https://"):
                return url
            return urljoin(strapi_url + "/", url.lstrip("/"))

        data = value.get("data")
        if isinstance(data, dict):
            attrs = data.get("attributes", data)
            return _media_url_from_value(attrs, strapi_url)
        if isinstance(data, list) and data:
            first = data[0]
            attrs = first.get("attributes", first) if isinstance(first, dict) else first
            return _media_url_from_value(attrs, strapi_url)

    return ""


def _normalize_image_item(item, strapi_url):
    if not isinstance(item, dict):
        return None

    attrs = item.get("attributes", item)
    color = _safe_get(attrs, "color", "name", default="default")
    image_alt = _safe_get(attrs, "image_alt", "alt", "alternativeText", "name", default="")
    image_path = _safe_get(attrs, "image_path", "image", "media", "photo", "url", default="")
    image_url = _media_url_from_value(image_path, strapi_url)

    if not image_url and "data" in attrs:
        image_url = _media_url_from_value(attrs, strapi_url)
    if not image_url:
        return None

    return {
        "image_path": image_url,
        "image_alt": image_alt,
        "color": str(color),
    }


def _normalize_images(raw_images, strapi_url):
    images = []

    if isinstance(raw_images, dict) and "data" in raw_images:
        data = raw_images.get("data")
        if isinstance(data, list):
            for item in data:
                normalized = _normalize_image_item(item, strapi_url)
                if normalized:
                    images.append(normalized)
            return images
        if isinstance(data, dict):
            normalized = _normalize_image_item(data, strapi_url)
            if normalized:
                images.append(normalized)
            return images

    for item in _as_list(raw_images):
        normalized = _normalize_image_item(item, strapi_url)
        if normalized:
            images.append(normalized)

    return images


def _normalize_product(entry, fallback_id, strapi_url):
    attrs = entry.get("attributes", entry) if isinstance(entry, dict) else {}
    raw_id = _safe_get(entry, "id", "documentId", default=None) if isinstance(entry, dict) else None
    external_id = _safe_get(attrs, "external_id", default="")
    product_id = str(external_id or raw_id or fallback_id)

    images = _normalize_images(_safe_get(attrs, "images", "gallery_images", default=[]), strapi_url)
    primary_image = _media_url_from_value(_safe_get(attrs, "image_path", "image", "thumbnail", default=""), strapi_url)
    if not primary_image and images:
        primary_image = images[0]["image_path"]

    desc = _safe_get(attrs, "desc", "short_description", "summary", default="")
    description = _safe_get(attrs, "description", "long_description", default=desc)
    price = _safe_get(attrs, "price", "delivery_time", default="72 Hours Delivery")
    sizes = _as_list(_safe_get(attrs, "Sizes", "sizes", default=[]))
    extended_sizes = _as_list(_safe_get(attrs, "extended_sizes", "extendedSizes", default=[]))

    return {
        "id": product_id,
        "_cms_source": "strapi",
        "external_id": external_id,
        "name": _safe_get(attrs, "name", "title", default=f"Product {product_id}"),
        "category": _safe_get(attrs, "category", default="Custom"),
        "keywords": _as_list(_safe_get(attrs, "keywords", "tags", default=[])),
        "desc": desc,
        "description": description,
        "price": str(price),
        "Sizes": [str(s) for s in sizes],
        "extended_sizes": [str(s) for s in extended_sizes],
        "extended_moq": _safe_get(attrs, "extended_moq", "extendedMoq", default="100 MOQ"),
        "image_alt": _safe_get(attrs, "image_alt", "alt_text", default=_safe_get(attrs, "name", "title", default="Product")),
        "decorations": [str(x) for x in _as_list(_safe_get(attrs, "decorations", default=[]))],
        "delivery_time": _safe_get(attrs, "delivery_time", default="72 Hours Delivery"),
        "instructions": [str(x) for x in _as_list(_safe_get(attrs, "instructions", default=[]))],
        "discount": _safe_get(attrs, "discount", default=""),
        "colors_available": _safe_get(attrs, "colors_available", "colorsAvailable", default=""),
        "custom_color": _safe_get(attrs, "custom_color", "customColor", default=""),
        "product_details": [str(x) for x in _as_list(_safe_get(attrs, "product_details", "productDetails", default=[]))],
        "images": images,
        "image_path": primary_image,
    }


def _fetch_json(url, headers, timeout):
    req = Request(url=url, headers=headers)
    with urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload)


def _media_urls_from_value(value, strapi_url):
    urls = []
    if not value:
        return urls
    if isinstance(value, list):
        for item in value:
            urls.extend(_media_urls_from_value(item, strapi_url))
        return urls
    if isinstance(value, dict):
        data = value.get("data")
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    urls.extend(_media_urls_from_value(item.get("attributes", item), strapi_url))
            return urls
        if isinstance(data, dict):
            urls.extend(_media_urls_from_value(data.get("attributes", data), strapi_url))
            return urls

        if "url" in value and value["url"]:
            url = str(value["url"])
            if url.startswith("http://") or url.startswith("https://"):
                urls.append(url)
            else:
                urls.append(urljoin(strapi_url + "/", url.lstrip("/")))
    return urls


def get_homepage_content():
    strapi_url = os.getenv("STRAPI_URL", "").strip().rstrip("/")
    if not strapi_url:
        return None

    collection = os.getenv("STRAPI_HOME_COLLECTION", "homepages").strip("/") or "homepages"
    token = os.getenv("STRAPI_API_TOKEN", "").strip()
    timeout = int(os.getenv("STRAPI_TIMEOUT_SECONDS", "8"))

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    candidates = [collection]
    if collection.endswith("ies"):
        candidates.append(collection[:-3] + "y")
    elif collection.endswith("y"):
        candidates.append(collection[:-1] + "ies")
    elif collection.endswith("s"):
        candidates.append(collection[:-1])
    else:
        candidates.append(collection + "s")

    for coll in list(dict.fromkeys(candidates)):
        try:
            query = urlencode(
                {
                    "populate[hero_images]": "true",
                    "populate[common][populate]": "image",
                    "pagination[page]": 1,
                    "pagination[pageSize]": 1,
                }
            )
            endpoint = f"{strapi_url}/api/{coll}?{query}"
            payload = _fetch_json(endpoint, headers, timeout)
            data = payload.get("data", [])
            if not isinstance(data, list) or not data:
                continue
            row = data[0]
            attrs = row.get("attributes", row) if isinstance(row, dict) else {}

            hero_urls = []
            for key in ["hero_images", "hero_banners", "images", "banners", "hero"]:
                hero_urls = _media_urls_from_value(_safe_get(attrs, key, default=None), strapi_url)
                if hero_urls:
                    break
            if not hero_urls:
                hero_urls = _media_urls_from_value(_safe_get(attrs, "image", "image_path", default=None), strapi_url)

            def _service_image(*keys, default=""):
                for key in keys:
                    val = _safe_get(attrs, key, default=None)
                    media_url = _media_url_from_value(val, strapi_url)
                    if media_url:
                        return media_url
                    if isinstance(val, str) and val.strip():
                        return val.strip()
                return default

            common_items = _safe_get(attrs, "common", "services", "service_cards", default=[])
            if not isinstance(common_items, list):
                common_items = []

            def _component_title(i, default):
                if i < len(common_items) and isinstance(common_items[i], dict):
                    return _safe_get(common_items[i], "title", "name", default=default)
                return default

            def _component_description(i, default):
                if i < len(common_items) and isinstance(common_items[i], dict):
                    return _safe_get(common_items[i], "description", "desc", default=default)
                return default

            def _component_image(i, default):
                if i < len(common_items) and isinstance(common_items[i], dict):
                    media_url = _media_url_from_value(
                        _safe_get(common_items[i], "image", "media", "file", default=None),
                        strapi_url,
                    )
                    if media_url:
                        return media_url
                return default

            return {
                "hero_images": hero_urls,
                "hero_subtitle": _safe_get(attrs, "hero_subtitle", "banner_subtitle", default="Perfect for Summer Evenings"),
                "hero_title": _safe_get(attrs, "hero_title", "banner_title", default="Casual and Stylish for All Seasons"),
                "hero_price_text": _safe_get(attrs, "hero_price_text", "banner_price_text", default="Starting From"),
                "hero_price_value": _safe_get(attrs, "hero_price_value", "banner_price_value", default="$129"),
                "hero_cta_text": _safe_get(attrs, "hero_cta_text", "banner_cta_text", default="SHOP NOW"),
                "hero_cta_link": _safe_get(attrs, "hero_cta_link", "banner_cta_link", default="/shop"),
                "exclusive_offer_subtitle": _safe_get(attrs, "exclusive_offer_subtitle", "offer_subtitle", default="Services"),
                "exclusive_offer_title": _safe_get(attrs, "exclusive_offer_title", "offer_title", default="Discover Our Exclusive Offerings"),
                "exclusive_offer_cta_text": _safe_get(attrs, "exclusive_offer_cta_text", "offer_cta_text", default="Make a enquiry"),
                "exclusive_offer_cta_link": _safe_get(attrs, "exclusive_offer_cta_link", "offer_cta_link", default="#"),
                "service_1_title": _safe_get(attrs, "service_1_title", "white_label_title", default=_component_title(0, "White Label Clothing")),
                "service_1_description": _safe_get(attrs, "service_1_description", "white_label_description", default=_component_description(0, "Just starting out? Select from our catalogue of products, add your branding and you're good to go. A great solution for small businesses & startup clothing brands.")),
                "service_1_image": _service_image("service_1_image", "white_label_image", default=_component_image(0, "/static/services/1.svg")),
                "service_2_title": _safe_get(attrs, "service_2_title", "custom_manufacturing_title", default=_component_title(1, "Custom Clothing Manufacturing")),
                "service_2_description": _safe_get(attrs, "service_2_description", "custom_manufacturing_description", default=_component_description(1, "Looking for something unique? With our expert guidance, you can design fully custom products, selecting everything from fabrics and sizing to adding your own creative twist. We'll support you every step of the way.")),
                "service_2_image": _service_image("service_2_image", "custom_manufacturing_image", default=_component_image(1, "/static/services/2.svg")),
                "service_3_title": _safe_get(attrs, "service_3_title", "garment_design_title", default=_component_title(2, "Garment Design Services")),
                "service_3_description": _safe_get(attrs, "service_3_description", "garment_design_description", default=_component_description(2, "Need assistance with bringing your ideas to life? We cover everything from start to finish and help businesses with their brand development.")),
                "service_3_image": _service_image("service_3_image", "garment_design_image", default=_component_image(2, "/static/services/3.svg")),
            }
        except HTTPError as exc:
            if exc.code == 404:
                continue
            logger.warning("Homepage fetch failed from Strapi: %s", exc)
            return None
        except (URLError, TimeoutError, ValueError) as exc:
            logger.warning("Homepage fetch failed from Strapi: %s", exc)
            return None

    return None


def _gallery_item_to_image(entry, strapi_url):
    attrs = entry.get("attributes", entry) if isinstance(entry, dict) else {}
    image_value = _safe_get(attrs, "image", "file", "media", "photo", default=None)
    image_url = _media_url_from_value(image_value, strapi_url)
    if not image_url:
        image_url = _media_url_from_value(_safe_get(attrs, "url", "image_path", default=""), strapi_url)
    if not image_url:
        return None

    label = _safe_get(attrs, "color", "title", "name", "alt_text", default="Gallery")
    order = _safe_get(attrs, "sort_order", "order", default=0)
    try:
        order = int(order)
    except Exception:
        order = 0

    return {
        "url": image_url,
        "color": str(label),
        "sort_order": order,
    }


def get_gallery_images():
    strapi_url = os.getenv("STRAPI_URL", "").strip().rstrip("/")
    if not strapi_url:
        return None

    collection = os.getenv("STRAPI_GALLERY_COLLECTION", "galleries").strip("/")
    if not collection:
        collection = "galleries"

    token = os.getenv("STRAPI_API_TOKEN", "").strip()
    timeout = int(os.getenv("STRAPI_TIMEOUT_SECONDS", "8"))

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    candidates = [collection]
    if collection.endswith("ies"):
        candidates.append(collection[:-3] + "y")
    elif collection.endswith("y"):
        candidates.append(collection[:-1] + "ies")
    elif collection.endswith("s"):
        candidates.append(collection[:-1])
    else:
        candidates.append(collection + "s")

    for coll in list(dict.fromkeys(candidates)):
        page = 1
        page_size = 100
        images = []
        try:
            while True:
                query = urlencode(
                    {
                        "populate": "*",
                        "pagination[page]": page,
                        "pagination[pageSize]": page_size,
                    }
                )
                endpoint = f"{strapi_url}/api/{coll}?{query}"
                payload = _fetch_json(endpoint, headers, timeout)
                data = payload.get("data", [])
                if not isinstance(data, list):
                    break

                for row in data:
                    normalized = _gallery_item_to_image(row, strapi_url)
                    if normalized:
                        images.append(normalized)

                pagination = payload.get("meta", {}).get("pagination", {})
                page_count = pagination.get("pageCount")
                if page_count is not None and page >= page_count:
                    break
                if len(data) < page_size:
                    break
                page += 1
        except HTTPError as exc:
            if exc.code == 404:
                continue
            logger.warning("Gallery fetch failed from Strapi: %s", exc)
            return None
        except (URLError, TimeoutError, ValueError) as exc:
            logger.warning("Gallery fetch failed from Strapi: %s", exc)
            return None

        images.sort(key=lambda x: x.get("sort_order", 0))
        return images

    logger.warning("Gallery fetch failed from Strapi: collection not found (%s)", collection)
    return None


def get_shop_products():
    strapi_url = os.getenv("STRAPI_URL", "").strip().rstrip("/")
    if not strapi_url:
        return None

    collection = os.getenv("STRAPI_PRODUCTS_COLLECTION", "products").strip("/")
    if not collection:
        collection = "products"

    token = os.getenv("STRAPI_API_TOKEN", "").strip()
    timeout = int(os.getenv("STRAPI_TIMEOUT_SECONDS", "8"))

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    page = 1
    page_size = 100
    all_products = {}

    try:
        while True:
            query = urlencode(
                {
                    "populate[images][populate]": "image",
                    "pagination[page]": page,
                    "pagination[pageSize]": page_size,
                }
            )
            endpoint = f"{strapi_url}/api/{collection}?{query}"
            payload = _fetch_json(endpoint, headers, timeout)
            data = payload.get("data", [])
            if not isinstance(data, list):
                break

            for index, row in enumerate(data, start=1):
                product = _normalize_product(row, fallback_id=f"{page}-{index}", strapi_url=strapi_url)
                if not str(product.get("external_id", "")).strip():
                    continue
                # Keep one record per external_id to avoid duplicates in storefront.
                all_products[str(product["id"])] = product

            pagination = payload.get("meta", {}).get("pagination", {})
            page_count = pagination.get("pageCount")
            if page_count is not None and page >= page_count:
                break
            if len(data) < page_size:
                break
            page += 1
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        logger.warning("Falling back to local shop.json because Strapi fetch failed: %s", exc)
        return None

    return all_products
