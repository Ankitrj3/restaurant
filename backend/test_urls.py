import urllib3
urllib3.disable_warnings()
import requests

q='[out:json];node["amenity"="restaurant"]["cuisine"~"indian|nepalese",i](around:32186.8, 30.5680447, -97.8029374);out body;'
urls = [
    'https://overpass-api.de/api/interpreter',
    'https://lz4.overpass-api.de/api/interpreter',
    'https://z.overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter'
]
for url in urls:
    try:
        r = requests.post(url, data=q, verify=False, timeout=5)
        print(f"URL: {url}")
        print(f"Status: {r.status_code}")
        print(f"Content: {r.text[:100]}")
    except Exception as e:
        print(f"URL: {url} failed: {e}")
