import urllib3
urllib3.disable_warnings()
import requests
q='[out:json];node["amenity"="restaurant"]["cuisine"~"indian",i](around:32186.8, 30.5680447, -97.8029374);out body;'
print(requests.post('https://overpass-api.de/api/interpreter', data=q, verify=False).text[:500])
