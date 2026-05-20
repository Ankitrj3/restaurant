import urllib3
urllib3.disable_warnings()
import requests, json

r = requests.get('http://localhost:5050/api/restaurants/search?radius=20', verify=False)
data = r.json()
print(f"Found: {data.get('competitors_found', 0)} restaurants")
for rest in data.get('restaurants', [])[:5]:
    print(f"  - {rest['name']} ({rest.get('distance_miles','?')} mi) [{rest.get('source','?')}]")
