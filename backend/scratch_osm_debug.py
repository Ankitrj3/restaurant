import requests
import json

overpass_url = "http://overpass-api.de/api/interpreter"
lat, lng = 30.5680447, -97.8029374
radius_meters = 25000  # ~15 miles

# Search specifically for nodes/ways containing "Chowrastha" or "Hashtag" or "India" or "Cuisine" within 15 miles
query = f"""
[out:json][timeout:25];
(
  node[~"name"~"Chowrastha|Hashtag|India|Desi",i](around:{radius_meters},{lat},{lng});
  way[~"name"~"Chowrastha|Hashtag|India|Desi",i](around:{radius_meters},{lat},{lng});
);
out center;
"""

print("Searching Overpass for name matches...")
try:
    headers = {'User-Agent': 'Bawarchi-Restaurant-Intelligence/1.0'}
    response = requests.post(overpass_url, data=query.encode('utf-8'), headers=headers, timeout=30)
    data = response.json()
    elements = data.get('elements', [])
    print(f"Total elements found: {len(elements)}")
    
    for el in elements:
        tags = el.get('tags', {})
        print(f"Name: {tags.get('name')}")
        print(f"  Amenity: {tags.get('amenity')}")
        print(f"  Cuisine: {tags.get('cuisine')}")
        print(f"  Tags: {tags}")
except Exception as e:
    print("Error:", e)
