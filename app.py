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

app = Flask(__name__)


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
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file()


def resolve_media_url(path):
    if not path:
        return url_for('static', filename='images/logo.png')
    cleaned = str(path).strip()
    if cleaned.startswith('http://') or cleaned.startswith('https://'):
        return cleaned
    return url_for('static', filename=cleaned.lstrip('/'))


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


def load_shop_products():
    products_from_strapi = get_shop_products()
    if products_from_strapi is not None:
        return products_from_strapi

    try:
        with open('content/shop.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def is_url_reachable(url, timeout=3):
    try:
        req = Request(url=url, method="GET")
        with urlopen(req, timeout=timeout):
            return True
    except HTTPError:
        return True
    except (URLError, TimeoutError, ValueError):
        return False

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
    return dict(resolve_media_url=resolve_media_url)

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
    home_content = get_homepage_content() or {
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
    allowed_ext = ('.png', '.jpg', '.jpeg', '.webp', '.gif')

    # Always discover gallery images from filesystem to ensure full catalog coverage.
    abc_root = os.path.join(app.static_folder, 'abc_upload')
    if os.path.isdir(abc_root):
        for root, _, files in os.walk(abc_root):
            color = os.path.basename(root)
            for file_name in sorted(files, key=lambda x: x.lower()):
                if not file_name.lower().endswith(allowed_ext):
                    continue
                full_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(full_path, app.static_folder).replace("\\", "/")
                if rel_path in seen_paths:
                    continue
                seen_paths.add(rel_path)
                all_gallery_images.append({
                    'url': resolve_media_url(rel_path),
                    'color': color
                })

    # Merge optional Strapi gallery collection entries without duplicates.
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
    random.shuffle(all_gallery_images)

    page = request.args.get('page', 1, type=int)
    per_page = 12
    total_images = len(all_gallery_images)
    total_pages = max(1, (total_images + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

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
    products_dict = load_shop_products()
    all_products = [{"id": k, **v} for k, v in products_dict.items()]

    page = request.args.get('page', 1, type=int)
    per_page = 12

    total_products = len(all_products)
    total_pages = (total_products + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    current_products = all_products[start_idx:end_idx]
    
    return render_template('shop.html', 
                         products=current_products,
                         current_page=page,
                         total_pages=total_pages)

@app.route('/shop-details')
def shop_details():
    """Handle shop details page with error handling and data validation."""
    product_id = request.args.get('id')
    
    if not product_id:
        flash('Product ID is required', 'error')
        return redirect(url_for('shop'))

    try:
        products_dict = load_shop_products()

        product = products_dict.get(product_id)
        
        if product is None:
            flash('Product not found', 'error')
            return redirect(url_for('shop')), 404
        product = {'id': product_id, **product}

        # Process extended sizes if available
        if 'extended_sizes' in product:
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

        # Build color images using explicit image list first (works for local and Strapi).
        product['color_images'] = {}
        images = product.get('images', []) or []
        for img in images:
            color = img.get('color', 'default')
            img_path = img.get('image_path')
            if not img_path:
                continue
            resolved = resolve_media_url(img_path)
            product['color_images'].setdefault(color, [])
            if resolved not in product['color_images'][color]:
                product['color_images'][color].append(resolved)

        # Prefer full color folder coverage from filesystem when folders are available.
        # This enables multiple-image sliders per color (e.g., 8 angles per color).
        for color in list(product['color_images'].keys()):
            folder = os.path.join('static', 'abc_upload', product.get('name', ''), color)
            if not os.path.isdir(folder):
                continue
            files = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
            files.sort(key=lambda x: (x.lower() != f"{color}.png", x))
            product['color_images'][color] = [
                resolve_media_url(f"abc_upload/{product.get('name', '')}/{color}/{f}")
                for f in files
            ]

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
        if not product['color_images'] and product.get('image_path'):
            resolved = resolve_media_url(product['image_path'])
            product['color_images'] = {'default': [resolved]}
            product['available_colors'] = ['default']
        product['description_text'] = description_to_text(product.get('description')) or product.get('desc', '')

        return render_template(
            'shop-details.html',
            product=product,
            phone_number=SystemConfig.COMPANY_PHONE,
            error=None
        )

    except FileNotFoundError:
        app.logger.error('Shop data file not found')
        flash('Product data unavailable', 'error')
        return redirect(url_for('shop')), 500
    except json.JSONDecodeError:
        app.logger.error('Invalid shop data format')
        flash('Invalid product data', 'error')
        return redirect(url_for('shop')), 500
    except Exception as e:
        app.logger.error(f'Unexpected error: {str(e)}')
        flash('An unexpected error occurred', 'error')
        return redirect(url_for('shop')), 500

@app.route('/search/api')
def search_api():
    """API endpoint for live search results"""
    query = request.args.get('q', '').strip().lower()
    category = request.args.get('category', '')
    
    if not query or len(query) < 2:
        return jsonify([])
    
    products_dict = load_shop_products()
    
    results = []
    for product_id, product in products_dict.items():
        # Search in name, description, and keywords
        search_text = f"{product.get('name', '')} {product.get('desc', '')} {' '.join(product.get('keywords', []))}".lower()
        
        # Category filter
        if category and category != '1':  # '1' is "All Apparels"
            product_category = product.get('category', '').lower()
            category_map = {
                '2': 'men',
                '3': 'women', 
                '4': 'kids'
            }
            if category in category_map and category_map[category] not in product_category:
                continue
        
        # Check if query matches
        if query in search_text:
            results.append({
                'id': product_id,
                'name': product.get('name', ''),
                'desc': product.get('desc', '')[:100] + '...' if len(product.get('desc', '')) > 100 else product.get('desc', ''),
                'image': resolve_media_url(product.get('image_path')),
                'price': product.get('price', ''),
                'url': f'/shop-details?id={product_id}'
            })
    
    # Limit results to 8 items
    return jsonify(results[:8])


@app.route('/cms')
def cms_panel():
    strapi_admin_url = os.getenv('STRAPI_ADMIN_URL', '').strip()
    strapi_url = os.getenv('STRAPI_URL', '').strip().rstrip('/')
    if not strapi_admin_url and strapi_url:
        strapi_admin_url = f"{strapi_url}/admin"

    if strapi_admin_url and is_url_reachable(strapi_admin_url):
        return redirect(strapi_admin_url)

    if strapi_admin_url:
        flash('CMS is configured but Strapi admin is not reachable. Start Strapi and try again.', 'error')
        return redirect(url_for('shop'))

    flash('CMS is not configured. Set STRAPI_ADMIN_URL or STRAPI_URL.', 'error')
    return redirect(url_for('shop'))


@app.route('/cms/admin')
def cms_admin_redirect():
    return redirect(url_for('cms_panel'))

if __name__ == '__main__':
    app.run(debug=True)
