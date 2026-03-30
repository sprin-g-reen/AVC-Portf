import os

file_path = "app.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.startswith("@app.route('/shop-details')"):
        start_idx = i
    if line.startswith("@app.route('/search/api')"):
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    new_func = """@app.route('/shop-details')
@app.route('/product/<product_id>')
def shop_details(product_id=None):
    \"\"\"Handle shop details page with error handling and data validation.\"\"\"
    product_id = product_id or request.args.get('id')
    
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
        product['brand'] = derive_brand(product)
        requested_color = request.args.get('color', '').strip()

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

        # Resolve requested color to an available color key.
        selected_color = ''
        if product['available_colors']:
            lookup = {normalize_text(c): c for c in product['available_colors']}
            selected_color = lookup.get(normalize_text(requested_color), product['available_colors'][0])

        # Build related products suggestions.
        related_candidates = []
        for pid, pdata in products_dict.items():
            if pid == product_id:
                continue
            pdata = {'id': pid, **pdata}
            pdata['brand'] = derive_brand(pdata)
            score = 0
            if normalize_text(pdata.get('category')) == normalize_text(product.get('category')):
                score += 3
            if normalize_text(pdata.get('brand')) == normalize_text(product.get('brand')):
                score += 2
            kw_a = {normalize_text(k) for k in product.get('keywords', [])}
            kw_b = {normalize_text(k) for k in pdata.get('keywords', [])}
            score += len(kw_a.intersection(kw_b))
            related_candidates.append((score, pdata))

        related_candidates.sort(key=lambda x: x[0], reverse=True)
        related_products = [item[1] for item in related_candidates[:4]]

        return render_template(
            'shop-details.html',
            product=product,
            selected_color=selected_color,
            related_products=related_products,
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

"""
    new_lines = lines[:start_idx] + [new_func] + lines[end_idx:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("Successfully updated shop_details")
else:
    print("Could not find start/end functions!")
