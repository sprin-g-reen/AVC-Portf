import os
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode

url = "https://cms.apparelbrandingcompany.in/api/products"
token = "b3ce273628820029da2f7774b86ddc1fb965cafbb59c007b48c47777b5c97a8db7a29fceba3a937120786f3aca8e15b073b2da16ec79d88ddaa8a4f5c47f2d1433387a4320959080896485d5186a8985c20d9a3f155c4ef5edb83c7dfd0d691c21059918859daf63e5b68c9e5fc6c29245984be7b57aeef893fb1882f751c9ee"

headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

try:
    # 1. First fetch with their current query
    query1 = urlencode({
        "populate[image]": "true",
        "populate[image_path]": "true",
        "populate[color]": "true",
        "populate[images][populate][image]": "true",
        "sort[0]": "updatedAt:desc",
        "pagination[page]": 1,
        "pagination[pageSize]": 2,
    })
    req1 = Request(f"{url}?{query1}", headers=headers)
    with urlopen(req1) as f:
        print("--- QUERY 1 (Current) ---")
        print(json.dumps(json.loads(f.read().decode())['data'][:1], indent=2))
        
    # 2. Second fetch with populate=*
    query2 = urlencode({
        "populate": "*",
        "sort[0]": "updatedAt:desc",
        "pagination[page]": 1,
        "pagination[pageSize]": 2,
    })
    req2 = Request(f"{url}?{query2}", headers=headers)
    with urlopen(req2) as f:
        print("\n--- QUERY 2 (Populate *) ---")
        print(json.dumps(json.loads(f.read().decode())['data'][:1], indent=2))

except Exception as e:
    print("Error:", e)
