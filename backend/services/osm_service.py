import requests
import json
import time

class OSMService:
    def __init__(self):
        self.overpass_url = "http://overpass-api.de/api/interpreter"

    def search_nearby_restaurants(self, lat, lng, radius_miles=5):
        """
        Use Overpass API to find Indian restaurants within radius.
        radius in Overpass is in meters. 1 mile = 1609.34 meters.
        """
        radius_meters = int(radius_miles * 1609.34)
        
        # We search for amenity=restaurant and cuisine=indian
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="restaurant"]["cuisine"~"indian"](around:{radius_meters},{lat},{lng});
          way["amenity"="restaurant"]["cuisine"~"indian"](around:{radius_meters},{lat},{lng});
          relation["amenity"="restaurant"]["cuisine"~"indian"](around:{radius_meters},{lat},{lng});
        );
        out center;
        """
        
        print(f"[OSM] Querying Overpass API for radius {radius_miles} miles...")
        try:
            headers = {'User-Agent': 'Bawarchi-Restaurant-Intelligence/1.0'}
            response = requests.post(self.overpass_url, data=query.encode('utf-8'), headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            restaurants = []
            for element in data.get('elements', []):
                tags = element.get('tags', {})
                name = tags.get('name')
                if not name:
                    continue
                    
                # Determine lat/lon
                r_lat = element.get('lat') or element.get('center', {}).get('lat')
                r_lon = element.get('lon') or element.get('center', {}).get('lon')
                
                if not r_lat or not r_lon:
                    continue
                    
                address = f"{tags.get('addr:housenumber', '')} {tags.get('addr:street', '')}, {tags.get('addr:city', '')}, {tags.get('addr:state', '')}".strip(" ,")
                if not address:
                    address = "Address unavailable"
                    
                restaurants.append({
                    "name": name,
                    "address": address,
                    "phone": tags.get('phone', ''),
                    "website_url": tags.get('website', ''),
                    "latitude": float(r_lat),
                    "longitude": float(r_lon),
                    "cuisine_tags": ["Indian"]
                })
                
            # Guarantee that Desi Chowrastha and Hashtag India are always included (often missing/misclassified in OSM tags)
            special_competitors = [
                {
                    "name": "Desi Chowrastha",
                    "address": "14201 Ronald Reagan Blvd Suite 110, Leander, TX 78641, United States",
                    "phone": "+1-512-528-5660",
                    "website_url": "https://desichowrastha.com/",
                    "latitude": 30.548480,
                    "longitude": -97.788500,
                    "cuisine_tags": ["Indian"]
                },
                {
                    "name": "Hashtag India",
                    "address": "13851 Ronald Reagan Blvd Suite 100, Cedar Park, TX 78613, United States",
                    "phone": "+1-512-986-7788",
                    "website_url": "https://hashtagindiatx.com/",
                    "latitude": 30.542100,
                    "longitude": -97.788100,
                    "cuisine_tags": ["Indian"]
                }
            ]
            for sc in special_competitors:
                if not any(sc['name'].lower() in r['name'].lower() for r in restaurants):
                    restaurants.append(sc)

            return restaurants
        except Exception as e:
            print(f"[OSM] Error querying Overpass API: {e}")
            return []

osm_service = OSMService()
