import logging
from app import load_env_file
from strapi_client import get_homepage_content

logging.basicConfig(level=logging.DEBUG)
load_env_file()
res = get_homepage_content()
if res is None:
    print("get_homepage_content returned None (failed)")
else:
    print("Got homepage content successfully.")
