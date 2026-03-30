from flask import Flask, render_template, request, redirect, url_for, g, flash, jsonify
from config import SystemConfig, SocialConfig
from threading import Thread
from helpers import send_email_admin
from strapi_client import get_shop_products, get_gallery_images, get_homepage_content
import json
import os
import random
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import requests

app = Flask(__name__)

def safe_fetch(url, headers=None):
    try:
        res = requests.get(url, headers=headers, timeout=5)

        if res.status_code != 200:
            print("API ERROR:", res.text)
            return None

        return res.json()

    except requests.exceptions.Timeout:
        print("Request timeout:", url)
        return None

    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return None

def load_env_file(path=".env"):
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ[key] = value


load_env_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def resolve_media_url(path):
    if not path:
        return url_for('static', filename='images/logo.png')

    cleaned = str(path).strip()

    # already full URL (Strapi CDN)
    if cleaned.startswith('http://') or cleaned.startswith('https://'):
        return cleaned

    # 🔥 FIX: prepend Strapi base URL
    return f"https://cms.apparelbrandingcompany.in{cleaned}"


def description_to_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        chunks = []
        for block in value:
            if not isinstance(block, dict):
                continue
            children = block.get("children", [])
            if isinstance(children, list):
                for child in children:
                    if isinstance(child, dict):
                        text = child.get("text")
                        if text:
                            chunks.append(str(text))
        return " ".join(chunks).strip()
    return ""


def normalize_text(value):
    return str(value or "").strip().lower()


def derive_brand(product):
    explicit = product.get("brand") or product.get("Brand")
    if explicit:
        return str(explicit).strip()
    name = str(product.get("name", "")).strip()
    if not name:
        return "General"
    return name.split()[0].title()


def load_shop_products():
    products_from_strapi = get_shop_products()
    if products_from_strapi is not None:
        return products_from_strapi
    return {}


def default_home_content():
    return {
        "logo_url": "/static/img/logo.png",
        "header_ticker_items": ["limited time offer"],
        "nav_links": [
            {"label": "Home", "url": "/"},
            {"label": "Branding Services", "url": "/shop"},
            {"label": "InStock Apparel", "url": "/shop"},
            {"label": "Our Gallery", "url": "/gallery"},
            {"label": "Testimonials", "url": "/testimonials"},
            {"label": "Contact Us", "url": "/contact"},
            {"label": "FAQ", "url": "/faq"},
            {"label": "About Us", "url": "/about"},
        ],
        "hero_images": [
            "/static/hero_mac/1.png",
            "/static/hero_mac/2.png",
            "/static/hero_mac/3.png",
        ],
        "hero_subtitle": "Perfect for Summer Evenings",
        "hero_title": "Casual and Stylish for All Seasons",
        "hero_price_text": "Starting From",
        "hero_price_value": "$129",
        "hero_cta_text": "SHOP NOW",
        "hero_cta_link": "/shop",
        "trusted_title": "our work is trusted by big brands",
        "trusted_description": "We've supplied clothing and merchandise to some of the largest organisations over the last 5 years. Check out the services we've supplied brands of all sizes below.",
        "trusted_brand_images": [
            "/static/brands/1.svg",
            "/static/brands/2.svg",
            "/static/brands/3.svg",
            "/static/brands/4.svg",
            "/static/brands/5.svg",
            "/static/brands/6.svg",
            "/static/brands/7.svg",
            "/static/brands/8.svg",
        ],
        "exclusive_offer_subtitle": "Services",
        "exclusive_offer_title": "Discover Our Exclusive Offerings",
        "exclusive_offer_cta_text": "Make a enquiry",
        "exclusive_offer_cta_link": "#",
        "services": [
            {
                "title": "White Label Clothing",
                "description": "Just starting out? Select from our catalogue of products, add your branding and you're good to go. A great solution for small businesses & startup clothing brands.",
                "image": "/static/services/1.svg",
            },
            {
                "title": "Custom Clothing Manufacturing",
                "description": "Looking for something unique? With our expert guidance, you can design fully custom products, selecting everything from fabrics and sizing to adding your own creative twist. We'll support you every step of the way.",
                "image": "/static/services/2.svg",
            },
            {
                "title": "Garment Design Services",
                "description": "Need assistance with bringing your ideas to life? We cover everything from start to finish and help businesses with their brand development.",
                "image": "/static/services/3.svg",
            },
            {
                "title": "Web Development Services",
                "description": "Need a strong digital presence? We build fast, responsive business and e-commerce websites aligned with your brand and growth goals.",
                "image": "/static/services/2.svg",
            },
        ],
        "footer_columns": [
            {
                "title": "Our Products",
                "links": [
                    {"label": "Customized T-Shirts", "url": "/shop"},
                    {"label": "Customized Shirts", "url": "/shop"},
                    {"label": "Customized Trousers", "url": "/shop"},
                    {"label": "Customized Hoodies", "url": "/shop"},
                    {"label": "Customized Caps", "url": "/shop"},
                ],
            },
            {
                "title": "White Papers",
                "links": [
                    {"label": "Corporate Uniforms", "url": "/shop?category=Corporate%20Uniforms"},
                    {"label": "School Uniforms", "url": "/shop?category=School%20Uniforms"},
                    {"label": "Sports Uniforms", "url": "/shop?category=Sports%20Uniforms"},
                    {"label": "Hospital Uniforms", "url": "/shop?category=Hospital%20Uniforms"},
                    {"label": "Hotel Uniforms", "url": "/shop?category=Hotel%20Uniforms"},
                ],
            },
        ],
        "footer_connect_title": "Connect with us",
        "footer_support_title": "Need help? Call now!",
        "footer_phone": SystemConfig.COMPANY_PHONE,
        "footer_brand_logo_url": "/static/img/logo.png",
        "footer_copyright": "Apparel Branding Company - All Rights Reserved; Created with love by Platfware",
        "footer_payment_image_url": "/static/img/payment-methods.png",
    }


def load_home_content():
    from_cms = get_homepage_content()
    if from_cms is not None:
        return from_cms
    return default_home_content()


def is_url_reachable(url, timeout=3):
    try:
        req = Request(url=url, method="GET")
        with urlopen(req, timeout=timeout):
            return True
    except HTTPError:
        return True
    except (URLError, TimeoutError, ValueError):
        return False


def extract_images(p):
    BASE = "https://cms.apparelbrandingcompany.in"
    images = []
    main_image = None

    try:
        for img in p.get("images", []):
            color = img.get("color", "default")

            for i in img.get("image", []):
                url = i.get("url")
                if not url:
                    continue

                full_url = BASE + url

                images.append({
                    "image_path": full_url,
                    "color": color
                })

                if not main_image:
                    main_image = full_url

    except Exception as e:
        print("Image parsing error:", e)

    return main_image, images

@app.context_processor
def inject_globals():
    g.facebook_url = SocialConfig.FACEBOOK_URL
    g.twitter_url = SocialConfig.TWITTER_URL
    g.instagram_url = SocialConfig.INSTAGRAM_URL
    g.youtube_url = SocialConfig.YOUTUBE_URL
    g.company_name = SystemConfig.COMPANY_NAME
    g.company_address = SystemConfig.COMPANY_ADDRESS
    g.company_phone = SystemConfig.COMPANY_PHONE
    g.company_email = SystemConfig.COMPANY_EMAIL
    g.crisp_website_id = SystemConfig.CRISP_WEBSITE_ID
    return dict(
        resolve_media_url=resolve_media_url,
        site_content=getattr(g, "site_content", default_home_content()),
        crisp_website_id=SystemConfig.CRISP_WEBSITE_ID,
    )


@app.before_request
def inject_site_content():
    g.site_content = load_home_content()


# setup sttaic folder
app.static_folder = 'static'
app.static_url_path = '/static'
app.secret_key = "MustBeChangedInProduction"


@app.route('/')
def index():
    try:
        with open('content/reviews.json', 'r', encoding='utf-8') as f:
            all_reviews = json.load(f)
    except FileNotFoundError:
        all_reviews = []

    page = request.args.get('page', 1, type=int)
    per_page = 16  # 4x4 grid

    total_reviews = len(all_reviews)
    total_pages = (total_reviews + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    current_reviews = all_reviews[start_idx:end_idx]
    home_content = getattr(g, "site_content", {}) or {}

    return render_template('index.html', reviews=current_reviews,
                           home_content=home_content,
                           current_page=page,
                           total_pages=total_pages)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/gallery')
def gallery():
    all_gallery_images = []
    seen_paths = set()

<<<<<<< HEAD
    # Images are now fully driven by Strapi, discarding the local folder fallback
    gallery_from_strapi = get_gallery_images() or []
    for item in gallery_from_strapi:
        image_url = item.get('url')
        if not image_url:
            continue
        if image_url in seen_paths:
            continue
        seen_paths.add(image_url)
        all_gallery_images.append({
            'url': image_url,
            'color': item.get('color', 'Gallery')
        })

    # Randomize order so colors are mixed in gallery.
=======
    abc_root = os.path.join(app.static_folder, 'abc_upload')

    max_images = 300  # prevent memory overload

    if os.path.isdir(abc_root):
        for root, _, files in os.walk(abc_root):
            color = os.path.basename(root)

            for file_name in sorted(files):
                if len(all_gallery_images) >= max_images:
                    break

                if not file_name.lower().endswith(allowed_ext):
                    continue

                full_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(full_path, app.static_folder).replace("\\", "/")

                if rel_path in seen_paths:
                    continue

                seen_paths.add(rel_path)

                all_gallery_images.append({
                    'url': url_for('static', filename=rel_path),
                    'color': color
                })

>>>>>>> f3025387d8e2326436640e00906cf1ef18ad292d
    random.shuffle(all_gallery_images)

    page = request.args.get('page', 1, type=int)
    per_page = 12

    total_images = len(all_gallery_images)
    total_pages = max(1, (total_images + per_page - 1) // per_page)

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    current_gallery_images = all_gallery_images[start_idx:end_idx]

    return render_template(
        'gallery.html',
        gallery_images=current_gallery_images,
        current_page=page,
        total_pages=total_pages
    )


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    with open('content.json', 'r', encoding='utf-8') as f:
        content = json.load(f)['contact.html']

    return render_template('contact.html', content=content)


@app.route('/faq')
def faq():
    return render_template('faq.html')


@app.route('/testimonials')
def testimonials():
    try:
        with open('content/reviews.json', 'r', encoding='utf-8') as f:
            all_reviews = json.load(f)
    except FileNotFoundError:
        all_reviews = []

    page = request.args.get('page', 1, type=int)
    per_page = 16  # 4x4 grid

    total_reviews = len(all_reviews)
    total_pages = (total_reviews + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    current_reviews = all_reviews[start_idx:end_idx]

    return render_template('testimonials.html',
                           reviews=current_reviews,
                           current_page=page,
                           total_pages=total_pages)


@app.route('/shop')
def shop():

    products_dict = {}   # ✅ ALWAYS DEFINE

    try:
        BASE = "https://cms.apparelbrandingcompany.in"
        TOKEN = os.getenv("STRAPI_API_TOKEN")  # ✅ single source

        url = f"{BASE}/api/products?populate=images.image&pagination[pageSize]=20"

        headers = {}
        if TOKEN:
            headers["Authorization"] = f"Bearer {TOKEN}"

        data = safe_fetch(url, headers)

        if not data:
            products = []
        else:
            products = data.get("data", [])


        for item in (data or {}).get("data", []):
            p = item

            # ✅ FIX IMAGE EXTRACTION
            all_images = []
            main_image = None

            try:
                for img in p.get("images", []):
                    color = img.get("color", "default")

                    for i in img.get("image", []):
                        url = i.get("url")
                        if not url:
                            continue

                        full_url = BASE + url

                        all_images.append({
                            "image_path": full_url,
                            "color": color
                        })

                        # set first image as main
                        if not main_image:
                            main_image = full_url

            except Exception as e:
                print("Image error:", e)

            products_dict[str(p.get("documentId"))] = {
                "id": p.get("id"),
                "documentId": p.get("documentId"),
                "name": p.get("name") or "No Name",
                "price": p.get("price") or "",
                "category": p.get("category") or "",
                "discount": p.get("discount") or "",
                "delivery_time": p.get("delivery_time") or "",
                "desc": p.get("desc") or "",
                "image_path": main_image   # ✅ NOW WORKS
                "image_alt": p.get("image_alt") or "",
                "images": all_images,
                "Sizes": p.get("sizes") or [],
                "extended_sizes": p.get("extended_sizes") or []
            }

    except Exception as e:
        print("🔥 STRAPI FAILED:", e)

    all_products = list(products_dict.values())

    for product in all_products:
        product['brand'] = derive_brand(product)
        images = product.get('images', []) or []
        available_colors = []
        for img in images:
            color = (img or {}).get('color')
            if color and color not in available_colors:
                available_colors.append(color)
        if not available_colors and product.get('image_path'):
            available_colors = ['default']
        product['available_colors'] = available_colors

    selected_filters = {
        'brand': request.args.get('brand', '').strip(),
        'size': request.args.get('size', '').strip(),
        'delivery': request.args.get('delivery', '').strip(),
        'category': request.args.get('category', '').strip(),
        'color': request.args.get('color', '').strip(),
    }

    filter_options = {
        'brands': sorted({p.get('brand', 'General') for p in all_products}),
        'sizes': sorted({size for p in all_products for size in (p.get('Sizes') or [])}),
        'deliveries': sorted({p.get('delivery_time', '').strip() for p in all_products if p.get('delivery_time')}),
        'categories': sorted({p.get('category', '').strip() for p in all_products if p.get('category')}),
        'colors': sorted({c for p in all_products for c in (p.get('available_colors') or []) if c}),
    }

    def product_matches(product):
        if selected_filters['brand']:
            if selected_filters['brand'].lower() not in (product.get('brand') or '').lower():
                return False

        if selected_filters['category']:
            if selected_filters['category'].lower() not in (product.get('category') or '').lower():
                return False

        if selected_filters['delivery']:
            if selected_filters['delivery'].lower() not in (product.get('delivery_time') or '').lower():
                return False

        if selected_filters['size']:
            all_sizes = set((product.get('Sizes') or []) + (product.get('extended_sizes') or []))
            if selected_filters['size'] not in all_sizes:
                return False

        return True

    filtered_products = [p for p in all_products if product_matches(p)]

    page = request.args.get('page', 1, type=int)
    per_page = 12

    total_products = len(filtered_products)
    total_pages = (total_products + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    current_products = filtered_products[start_idx:end_idx]

    return render_template('shop.html',
                           products=current_products,
                           current_page=page,
                           total_pages=total_pages,
                           filter_options=filter_options,
                           selected_filters=selected_filters)


@app.route('/shop-details')
@app.route('/product/<product_id>')
def shop_details(product_id=None):
    """Handle shop details page with error handling and data validation."""

    product_id = product_id or request.args.get('id')

    if not product_id:
        flash('Product ID is required', 'error')
        return redirect(url_for('shop'))

    try:
        BASE = "https://cms.apparelbrandingcompany.in"
        TOKEN = os.getenv("STRAPI_API_TOKEN")

        print("STEP 1: route started")

        # ✅ Strapi v5 filter (correct)
        import time

        url = (
            f"{BASE}/api/products"
            f"?populate[images][populate]=image"
            f"&pagination[pageSize]=20"
            f"&sort=createdAt:desc"
            f"&_={int(time.time())}"
        )

        headers = {}
        if TOKEN:
            headers["Authorization"] = f"Bearer {TOKEN}"

        print("STEP 2: calling API", url)

        data = safe_fetch(url, headers)

        if not data:
            flash('Failed to fetch product', 'error')
            return redirect(url_for('shop'))

        product_data = data.get("data", [])

        # ✅ FIND CORRECT PRODUCT USING documentId
        p = None
        for item in product_data:
            if str(item.get("documentId")) == str(product_id):
                p = item
                break

        # ✅ HANDLE NOT FOUND
        if not p:
            print("Product not found:", product_id)
            flash('Product not found', 'error')
            return redirect(url_for('shop'))

        # ✅ FIXED IMAGE HANDLING (Strapi v5 safe)

        try:
            images = p.get("images", [])

            if images and len(images) > 0:
                first = images[0]

                if first.get("image") and len(first["image"]) > 0:
                    image_url = "https://cms.apparelbrandingcompany.in" + first["image"][0]["url"]

        except Exception as e:
            print("Details image error:", e)

        # ✅ Build product object
        product = {
            "id": str(p.get("id")),
            "documentId": p.get("documentId"),
            "name": p.get("name", ""),
            "desc": p.get("desc", ""),
            "description": p.get("description", ""),
            "category": p.get("category", ""),
            "price": p.get("price", ""),
            "delivery_time": p.get("delivery_time", ""),
            "image_path": main_image,
            "image_alt": p.get("image_alt", ""),
            "images": all_images,
            "Sizes": p.get("sizes", []),
            "extended_sizes": p.get("extended_sizes", [])
        }

        # ✅ Brand
        product['brand'] = derive_brand(product)

        # ✅ Sizes structure
        product['all_sizes'] = {
            'regular': {
                'sizes': product['Sizes'],
                'moq': 'No MOQ'
            },
            'extended': {
                'sizes': product['extended_sizes'],
                'moq': product.get('extended_moq', '100 MOQ')
            }
        }

        # ✅ Default images fallback
        if not product['images'] and product['image_path']:
            product['images'] = [{
                'image_path': product['image_path'],
                'image_alt': product.get('image_alt', product['name']),
                'color': 'default'
            }]

        # ✅ Color images
        product['color_images'] = {}
        for img in product['images']:
            color = img.get('color', 'default')
            img_path = img.get('image_path')

            if not img_path:
                continue

            resolved = resolve_media_url(img_path)

            product['color_images'].setdefault(color, [])
            if resolved not in product['color_images'][color]:
                product['color_images'][color].append(resolved)

<<<<<<< HEAD
        product['available_colors'] = list(product['color_images'].keys())
            
        # Ensure product has all required fields
        required_fields = ['name', 'desc', 'description', 'price', 'image_path', 'image_alt']
        for field in required_fields:
            if field not in product:
                product[field] = ''
        if not product.get('image_path'):
            product['image_path'] = 'images/logo.png'
        for list_field in ['Sizes', 'decorations', 'instructions', 'product_details']:
            if list_field not in product or not isinstance(product.get(list_field), list):
                product[list_field] = []
        if not product.get('images') and product.get('image_path'):
            product['images'] = [{
                'image_path': product['image_path'],
                'image_alt': product.get('image_alt', product.get('name', 'Product')),
                'color': 'default'
            }]
=======
        # ✅ Ensure at least one image
>>>>>>> f3025387d8e2326436640e00906cf1ef18ad292d
        if not product['color_images'] and product.get('image_path'):
            resolved = resolve_media_url(product['image_path'])
            product['color_images'] = {'default': [resolved]}

        product['available_colors'] = list(product['color_images'].keys())

        # ✅ Selected color
        requested_color = request.args.get('color', '').strip()
        selected_color = product['available_colors'][0] if product['available_colors'] else 'default'

        if requested_color:
            lookup = {normalize_text(c): c for c in product['available_colors']}
            selected_color = lookup.get(normalize_text(requested_color), selected_color)

        # ✅ Description text
        product['description_text'] = description_to_text(
            product.get('description')
        ) or product.get('desc', '')

        # -------------------------
        # ✅ RELATED PRODUCTS
        # -------------------------
        related_products = []

        from urllib.parse import quote

        try:
            category = product.get("category", "")
            product_id = product.get("documentId")

            rel_url = f"{BASE}/api/products?filters[category][$eq]={quote(category)}&populate[images][populate]=image&pagination[pageSize]=10"
            rel_res = requests.get(rel_url, timeout=5)

            if rel_res.status_code != 200:
                print("Related API failed:", rel_res.status_code)
                rel_data = []
            else:
                rel_data = rel_res.json().get("data", [])
    
                for item in rel_data:
                    if item.get("documentId") == product_id:
                        continue  

                    # ✅ GET IMAGE (MISSING LINE — CRITICAL FIX)
                    img_url = extract_image(item)

                    # ✅ MAKE FULL URL SAFELY
                    if img_url and not img_url.startswith("http"):
                        img_url = BASE + img_url

                    # ✅ FINAL FALLBACK
                    if not img_url:
                        img_url = "/static/images/logo.png"

                    related_products.append({    
                        "documentId": item.get("documentId"),
                        "name": item.get("name"),
                        "price": item.get("price"),
                        "image_path": img_url
                    })

            related_products = related_products[:4]


        except Exception as e:
            print("Related products error:", str(e))

        # -------------------------
        # ✅ FINAL RENDER
        # -------------------------
        return render_template(
            'shop-details.html',
            product=product,
            selected_color=selected_color,
            related_products=related_products,
            phone_number=SystemConfig.COMPANY_PHONE,
            error=None
        )

    # ✅ CRITICAL FIX (your crash reason)
    except Exception as e:
        print("ERROR in shop_details:", str(e))
        flash('Something went wrong', 'error')
        return redirect(url_for('shop'))


@app.route('/search/api')
def search_api():
    """API endpoint for live search results"""

    query = request.args.get('q', '').strip().lower()
    category = request.args.get('category', '')

    # Validate query
    if not query or len(query) < 2:
        return jsonify([])

    try:
        products_dict = load_shop_products()
        results = []

        for product_id, product in products_dict.items():

            # ✅ FIXED SEARCH TEXT (NO SYNTAX ERROR)
            search_text = (
                f"{product.get('name', '')} "
                f"{product.get('desc', '')} "
                f"{' '.join(product.get('keywords', []))}"
            ).lower()

            # -------------------------
            # CATEGORY FILTER
            # -------------------------
            if category and category != '1':  # '1' = All
                product_category = product.get('category', '').lower()

                category_map = {
                    '2': 'men',
                    '3': 'women',
                    '4': 'kids'
                }

                if category in category_map:
                    if category_map[category] not in product_category:
                        continue

            # -------------------------
            # MATCH SEARCH
            # -------------------------
            if query in search_text:

                desc = product.get('desc', '')

                results.append({
                    'id': product_id,
                    'name': product.get('name', ''),
                    'desc': desc[:100] + '...' if len(desc) > 100 else desc,
                    'image': resolve_media_url(product.get('image_path')),
                    'price': product.get('price', ''),
                    'url': f'/product/{product_id}'
                })

        # Limit results
        return jsonify(results[:8])

    except Exception as e:
        print("Search API ERROR:", str(e))
        return jsonify([])

# @app.route('/cms')
# def cms_panel():
#    strapi_admin_url = os.getenv('STRAPI_ADMIN_URL', '').strip()
#    strapi_url = os.getenv('STRAPI_URL', '').strip().rstrip('/')
#    if not strapi_admin_url and strapi_url:
#        strapi_admin_url = f"{strapi_url}/admin"

    # For network/proxy deployments, skip server-side reachability checks and
    # always redirect when a CMS URL is configured.
#    if strapi_admin_url:
#        return redirect(strapi_admin_url)
#
#    flash('CMS is not configured. Set STRAPI_ADMIN_URL or STRAPI_URL.', 'error')
#    return redirect(url_for('shop'))


# @app.route('/cms/admin')
# def cms_admin_redirect():
#    return redirect(url_for('cms_panel'))


@app.route('/debug/strapi-env')
def debug_strapi_env():
    import os
    from urllib.request import Request, urlopen
    import json

    strapi_url = os.getenv("STRAPI_URL", "NOT SET").strip().rstrip("/")
    token = os.getenv("STRAPI_API_TOKEN", "NOT SET").strip()
    collection = os.getenv("STRAPI_PRODUCTS_COLLECTION", "products").strip("/")

    # Show first and last 6 chars of token to verify it loaded correctly
    token_preview = f"{token[:6]}...{token[-6:]}" if len(token) > 12 else token

    headers = {"Accept": "application/json"}
    if token and token != "NOT SET":
        headers["Authorization"] = f"Bearer {token}"

    test_url = f"{strapi_url}/api/{collection}?pagination[pageSize]=1"

    try:
        req = Request(url=test_url, headers=headers)
        with urlopen(req, timeout=8) as r:
            body = json.loads(r.read().decode())
            return {
                "strapi_url": strapi_url,
                "collection": collection,
                "token_preview": token_preview,
                "token_length": len(token),
                "url_tested": test_url,
                "status": "SUCCESS",
                "product_count": body.get(
                    "meta",
                    {}).get(
                    "pagination",
                    {}).get("total"),
            }
    except Exception as e:
        return {
            "strapi_url": strapi_url,
            "collection": collection,
            "token_preview": token_preview,
            "token_length": len(token),
            "url_tested": test_url,
            "status": "FAILED",
            "error": str(e),
        }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
