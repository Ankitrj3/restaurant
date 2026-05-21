import requests

overpass_url = "http://overpass-api.de/api/interpreter"
lat, lng = 30.5680447, -97.8029374
radius_meters = 16093  # 10 miles

# Search exact names
query = f"""
[out:json][timeout:15];
(
  node(around:{radius_meters},{lat},{lng})["name"="Desi Chowrastha"];
  node(around:{radius_meters},{lat},{lng})["name"="Hashtag India"];
  way(around:{radius_meters},{lat},{lng})["name"="Desi Chowrastha"];
  way(around:{radius_meters},{lat},{lng})["name"="Hashtag India"];
);
out center;
"""

try:
    headers = {'User-Agent': 'Bawarchi-Restaurant-Intelligence/1.0'}
    response = requests.post(overpass_url, data=query.encode('utf-8'), headers=headers, timeout=20)
    print("Status:", response.status_code)
    data = response.json()
    elements = data.get('elements', [])
    print(f"Found {len(elements)} matches:")
    for el in elements:
        tags = el.get('tags', {})
        print(f"Name: {tags.get('name')}")
        print(f"  Type: {el.get('type')}")
        print(f"  Amenity: {tags.get('amenity')}")
        print(f"  Cuisine: {tags.get('cuisine')}")
        print(f"  All tags: {tags}")
except Exception as e:
    print("Error:", e)
