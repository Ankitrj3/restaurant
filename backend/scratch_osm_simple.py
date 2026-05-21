import requests

overpass_url = "http://overpass-api.de/api/interpreter"
lat, lng = 30.5680447, -97.8029374
radius_meters = 16093  # 10 miles

# Try a simpler, narrow search
query = """
[out:json][timeout:15];
node["amenity"="restaurant"](around:5000,30.5680447,-97.8029374);
out;
"""

try:
    headers = {'User-Agent': 'Bawarchi-Restaurant-Intelligence/1.0'}
    response = requests.post(overpass_url, data=query.encode('utf-8'), headers=headers, timeout=20)
    print("Status:", response.status_code)
    print("Body preview:", response.text[:300])
except Exception as e:
    print("Error:", e)
