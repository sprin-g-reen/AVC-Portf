import logging
from config import SystemConfig, SocialConfig
from app import load_env_file
from strapi_client import get_shop_products

logging.basicConfig(level=logging.DEBUG)

load_env_file()
res = get_shop_products()
if res is None:
    print("get_shop_products returned None (failed)")
else:
    print(f"Got {len(res)} products from Strapi.")
