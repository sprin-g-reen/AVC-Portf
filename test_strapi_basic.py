import os
from urllib.request import Request, urlopen
from app import load_env_file

load_env_file()
token = os.environ.get('STRAPI_API_TOKEN')
url = os.environ.get('STRAPI_URL') + '/api/products'

print(f"URL: {url}")
req = Request(url, headers={"Authorization": f"Bearer {token}"})
try:
    with urlopen(req) as f:
        print(f.read().decode()[:500])
except Exception as e:
    print("Error:", e)
