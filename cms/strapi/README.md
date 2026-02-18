# Strapi CMS Setup (Compatible with This Flask Project)

This project is now Strapi-ready.

## 1) Create Strapi app

Run this once from project root:

```bash
npx create-strapi-app@latest cms/strapi-app --quickstart
```

Alternative (Docker panel bootstrap included in repo):

```bash
docker compose -f cms/strapi/docker-compose.yml up -d
```

## 2) Create Product collection in Strapi

In Strapi Admin (`http://localhost:1337/admin`), create collection type `products`.

Recommended fields:

- `external_id` (Text, Unique)  
- `name` (Text, Required)  
- `category` (Text)
- `keywords` (JSON)
- `desc` (Text)
- `description` (Rich Text or Long Text)
- `price` (Text)
- `Sizes` (JSON)
- `extended_sizes` (JSON)
- `extended_moq` (Text)
- `image_alt` (Text)
- `decorations` (JSON)
- `delivery_time` (Text)
- `instructions` (JSON)
- `discount` (Text)
- `colors_available` (Text)
- `custom_color` (Text)
- `product_details` (JSON)
- `image_path` (Media, single) or Text
- `images` (Repeatable component recommended) for color variants:
  - `color` (Text)
  - `image` (Media, single)
  - `image_alt` (Text)

This gives admin direct control over:
- Product content (`name`, `desc`, `description`, etc.)
- Main image (`image_path`)
- Color variants (`images[].color` + `images[].image`)

## 2.1) Create Gallery collection in Strapi

Create collection type `gallery` for admin-managed gallery uploads/deletes.
Note: Strapi API ID is usually pluralized. In this project, set `STRAPI_GALLERY_COLLECTION=galleries`.

Recommended fields:

- `image` (Media, single, required)
- `title` (Text)
- `sort_order` (Number, default `0`)

How it works in this project:

- Flask route `/gallery` first reads Strapi `galleries`.
- If `galleries` is empty/unavailable, it falls back to product-based gallery logic.
- Admin can add/delete entries in `galleries` directly from Strapi Content Manager.

## 2.2) Create Homepage collection in Strapi

Create collection type `homepages` (single entry is enough).

Recommended fields:

- `hero_images` (Media, multiple)
- `hero_subtitle` (Text)
- `hero_title` (Text)
- `hero_price_text` (Text)
- `hero_price_value` (Text)
- `hero_cta_text` (Text)
- `hero_cta_link` (Text)
- `exclusive_offer_subtitle` (Text)
- `exclusive_offer_title` (Text)
- `exclusive_offer_cta_text` (Text)
- `exclusive_offer_cta_link` (Text)

How it works:

- Flask route `/` reads first entry from `homepages`.
- Hero slider images and Exclusive Offer heading/CTA are rendered from this collection.
- If no entry exists, current hardcoded defaults are used.

## 3) Enable API access

In Strapi:

1. Create an API token (Settings -> API Tokens).  
2. Give read/write access to `products` for the token role.
3. In Roles & Permissions, ensure your admin/editor role can:
   - `create`, `read`, `update`, `delete` on `products`
   - upload/update media in Media Library
3. Publish product entries.

## 4) Configure Flask app

Set environment variables:

```env
STRAPI_URL=http://localhost:1337
STRAPI_PRODUCTS_COLLECTION=products
STRAPI_GALLERY_COLLECTION=galleries
STRAPI_HOME_COLLECTION=homepages
STRAPI_API_TOKEN=your_strapi_api_token
STRAPI_ADMIN_URL=http://localhost:1337/admin
STRAPI_TIMEOUT_SECONDS=8
```

If Strapi is unavailable, Flask automatically falls back to `content/shop.json`.

## 5) Optional: Seed Strapi from existing `shop.json`

Use:

```bash
python scripts/sync_shop_to_strapi.py
```

Required env vars for sync:

- `STRAPI_URL`
- `STRAPI_API_TOKEN`
- optional `STRAPI_PRODUCTS_COLLECTION` (defaults to `products`)
