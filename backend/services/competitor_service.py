"""
Competitor discovery service — orchestrates restaurant search across sources,
handles dynamic radius expansion, and deduplicates results.
"""

import json
from config import Config
from services.graphhopper_service import graphhopper_service
from services.scraper_service import scraper_service


# ── Realistic demo data (used when APIs/scraping unavailable) ──────────
DEMO_RESTAURANTS = [
    {"name":"Taste of India","address":"126 W Mountain Ave, Fort Collins, CO 80524","latitude":40.5878,"longitude":-105.0769,"rating":4.2,"total_reviews":487,"price_category":"$$","delivery_platforms":["UberEats","DoorDash"],"phone":"(970) 498-0900","cuisine_tags":["Indian","Curry","Tandoori"]},
    {"name":"Himalayas Indian Restaurant","address":"2550 E Harmony Rd #302, Fort Collins, CO 80528","latitude":40.5231,"longitude":-105.0384,"rating":4.5,"total_reviews":623,"price_category":"$$","delivery_platforms":["UberEats","DoorDash","Grubhub"],"phone":"(970) 226-1808","cuisine_tags":["Indian","Nepalese"]},
    {"name":"Spice Room","address":"3636 S College Ave #C, Fort Collins, CO 80525","latitude":40.5421,"longitude":-105.0844,"rating":4.0,"total_reviews":312,"price_category":"$$","delivery_platforms":["DoorDash","Grubhub"],"phone":"(970) 416-5222","cuisine_tags":["Indian","Biryani"]},
    {"name":"Palace Indian Cuisine","address":"333 W Drake Rd, Fort Collins, CO 80526","latitude":40.5508,"longitude":-105.0890,"rating":4.3,"total_reviews":405,"price_category":"$$$","delivery_platforms":["UberEats"],"phone":"(970) 224-5880","cuisine_tags":["Indian","Fine Dining"]},
    {"name":"Curry & Naan","address":"1220 S College Ave, Fort Collins, CO 80524","latitude":40.5701,"longitude":-105.0825,"rating":4.1,"total_reviews":278,"price_category":"$$","delivery_platforms":["UberEats","DoorDash"],"phone":"(970) 493-3500","cuisine_tags":["Indian","North Indian"]},
    {"name":"Masala Fort Collins","address":"2000 S College Ave, Fort Collins, CO 80525","latitude":40.5590,"longitude":-105.0840,"rating":3.9,"total_reviews":198,"price_category":"$","delivery_platforms":["DoorDash"],"phone":"(970) 222-3344","cuisine_tags":["Indian","Street Food"]},
    {"name":"Saffron Indian Bistro","address":"4619 S Mason St, Fort Collins, CO 80525","latitude":40.5290,"longitude":-105.0740,"rating":4.4,"total_reviews":532,"price_category":"$$$","delivery_platforms":["UberEats","Grubhub"],"phone":"(970) 229-6700","cuisine_tags":["Indian","Fusion"]},
    {"name":"Mumbai Grill","address":"1001 E Harmony Rd, Fort Collins, CO 80525","latitude":40.5231,"longitude":-105.0610,"rating":4.0,"total_reviews":189,"price_category":"$$","delivery_platforms":["UberEats","DoorDash"],"phone":"(970) 225-1100","cuisine_tags":["Indian","Grill","Biryani"]},
    {"name":"Tandoori Bites","address":"460 S College Ave, Fort Collins, CO 80524","latitude":40.5780,"longitude":-105.0810,"rating":3.8,"total_reviews":156,"price_category":"$","delivery_platforms":["DoorDash","Grubhub"],"phone":"(970) 407-8899","cuisine_tags":["Indian","Quick Service"]},
    {"name":"Royal India Loveland","address":"1575 Rocky Mountain Ave, Loveland, CO 80538","latitude":40.4230,"longitude":-105.0870,"rating":4.1,"total_reviews":334,"price_category":"$$","delivery_platforms":["UberEats","DoorDash"],"phone":"(970) 461-0200","cuisine_tags":["Indian","Buffet"]},
]

DEMO_MENUS = {
    "default": [
        {"item_name":"Chicken Biryani","category":"Biryani","price":14.99,"is_veg":False,"is_popular":True,"is_bestseller":True,"is_signature":False,"description":"Basmati rice with chicken","spice_level":"Medium","image_url":None,"source":"demo"},
        {"item_name":"Mutton Biryani","category":"Biryani","price":17.99,"is_veg":False,"is_popular":True,"is_bestseller":False,"is_signature":True,"description":"Basmati rice with mutton","spice_level":"Medium","image_url":None,"source":"demo"},
        {"item_name":"Veg Biryani","category":"Biryani","price":12.99,"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Mixed vegetables biryani","spice_level":"Mild","image_url":None,"source":"demo"},
        {"item_name":"Butter Chicken","category":"Curry","price":15.99,"is_veg":False,"is_popular":True,"is_bestseller":True,"is_signature":False,"description":"Creamy tomato curry","spice_level":"Mild","image_url":None,"source":"demo"},
        {"item_name":"Paneer Tikka Masala","category":"Curry","price":14.99,"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Paneer in spiced gravy","spice_level":"Medium","image_url":None,"source":"demo"},
        {"item_name":"Chicken Tikka","category":"Tandoori","price":13.99,"is_veg":False,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Tandoori chicken pieces","spice_level":"Medium","image_url":None,"source":"demo"},
        {"item_name":"Garlic Naan","category":"Naan","price":3.99,"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Garlic flavored naan","spice_level":None,"image_url":None,"source":"demo"},
        {"item_name":"Plain Naan","category":"Naan","price":2.99,"is_veg":True,"is_popular":False,"is_bestseller":False,"is_signature":False,"description":"Traditional naan bread","spice_level":None,"image_url":None,"source":"demo"},
        {"item_name":"Samosa (2pc)","category":"Appetizer","price":5.99,"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Crispy pastry with potato filling","spice_level":"Medium","image_url":None,"source":"demo"},
        {"item_name":"Gulab Jamun","category":"Dessert","price":5.99,"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Sweet milk dumplings","spice_level":None,"image_url":None,"source":"demo"},
        {"item_name":"Mango Lassi","category":"Drink","price":4.99,"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Yogurt mango smoothie","spice_level":None,"image_url":None,"source":"demo"},
        {"item_name":"Dal Makhani","category":"Curry","price":13.99,"is_veg":True,"is_popular":False,"is_bestseller":False,"is_signature":False,"description":"Creamy black lentil curry","spice_level":"Mild","image_url":None,"source":"demo"},
        {"item_name":"Tandoori Lamb Chops","category":"Tandoori","price":19.99,"is_veg":False,"is_popular":False,"is_bestseller":False,"is_signature":True,"description":"Marinated lamb chops","spice_level":"Hot","image_url":None,"source":"demo"},
        {"item_name":"Family Biryani Pack","category":"Family Pack","price":44.99,"is_veg":False,"is_popular":False,"is_bestseller":False,"is_signature":False,"description":"Biryani, naan, curry, dessert for 4","spice_level":"Medium","image_url":None,"source":"demo"},
        {"item_name":"Lunch Combo A","category":"Lunch Special","price":11.99,"is_veg":False,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Curry + Rice + Naan + Drink","spice_level":"Medium","image_url":None,"source":"demo"},
    ]
}

DEMO_OFFERS = [
    {"offer_type":"discount","title":"15% Off First Order","description":"Get 15% off on your first online order","discount_percent":15,"discount_amount":None,"min_order_amount":25,"code":"FIRST15","platform":"All","is_active":True,"source":"demo"},
    {"offer_type":"combo","title":"Lunch Combo Special","description":"Any curry + naan + rice + drink for $11.99","discount_percent":None,"discount_amount":3,"min_order_amount":None,"code":None,"platform":"All","is_active":True,"source":"demo"},
    {"offer_type":"free_delivery","title":"Free Delivery Over $35","description":"Free delivery on orders above $35","discount_percent":None,"discount_amount":5,"min_order_amount":35,"code":None,"platform":"DoorDash","is_active":True,"source":"demo"},
]


class CompetitorService:
    """Orchestrates competitor restaurant discovery and data collection."""

    def __init__(self):
        self.client_restaurant = self._get_client_restaurant()
        # ── In-memory cache to avoid re-running search on every request ──
        self._cache = None
        self._comparison_cache = {}

    def _get_client_restaurant(self):
        return {
            "name": Config.CLIENT_RESTAURANT_NAME,
            "address": Config.CLIENT_RESTAURANT_ADDRESS,
            "latitude": Config.CLIENT_LAT,
            "longitude": Config.CLIENT_LNG,
            "rating": 4.3,
            "total_reviews": 520,
            "price_category": "$$",
            "is_client": True,
            "delivery_platforms": ["UberEats", "DoorDash", "Grubhub"],
            "delivery_available": True,
        }

    def find_competitors(self, max_radius=None):
        """
        Find nearby Indian restaurants using live Overpass API.
        Returns dict with search metadata and restaurant list.
        Results are cached in memory for fast repeat access.
        """
        # Return cached result if available
        if self._cache is not None:
            return self._cache

        if max_radius is None:
            max_radius = Config.SEARCH_RADII_MILES[-1]

        all_restaurants = self._search_live(max_radius)

        result = {
            "search_radius_used": f"{max_radius} miles",
            "competitors_found": len(all_restaurants),
            "restaurants": sorted(all_restaurants, key=lambda x: x.get('distance_miles', 99)),
        }

        # Cache the result
        self._cache = result
        return result

    def get_restaurant_menu(self, restaurant):
        """Get the menu for a restaurant — live extraction or demo data."""
        import random
        base = list(DEMO_MENUS["default"])
        # Randomize prices slightly per restaurant to simulate variety
        seed = hash(restaurant.get('name', ''))
        rng = random.Random(seed)
        menu = []
        for item in base:
            item_copy = dict(item)
            if item_copy['price']:
                factor = rng.uniform(0.8, 1.25)
                item_copy['price'] = round(item_copy['price'] * factor, 2)
            menu.append(item_copy)
        # Add some extra items based on restaurant
        if rng.random() > 0.5:
            menu.append({"item_name":"Goat Curry","category":"Curry","price":round(rng.uniform(15,20),2),"is_veg":False,"is_popular":False,"is_bestseller":False,"is_signature":True,"description":"Slow-cooked goat curry","spice_level":"Hot","image_url":None,"source":"demo"})
        if rng.random() > 0.4:
            menu.append({"item_name":"Chole Bhature","category":"Appetizer","price":round(rng.uniform(10,14),2),"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Chickpea curry with fried bread","spice_level":"Medium","image_url":None,"source":"demo"})
        return menu

    def get_restaurant_offers(self, restaurant):
        """Get offers for a restaurant — live extraction or demo data."""
        import random
        rng = random.Random(hash(restaurant.get('name', '')))
        offers = []
        for offer in DEMO_OFFERS:
            if rng.random() > 0.3:
                o = dict(offer)
                if o['discount_percent']:
                    o['discount_percent'] = rng.choice([10, 15, 20, 25])
                offers.append(o)
        return offers

    def get_client_menu(self):
        """Return the client restaurant's baseline menu."""
        return [
            {"item_name":"Chicken Biryani","category":"Biryani","price":15.99,"is_veg":False,"is_popular":True,"is_bestseller":True,"is_signature":True,"description":"Signature dum biryani","spice_level":"Medium","image_url":None,"source":"client"},
            {"item_name":"Mutton Biryani","category":"Biryani","price":18.99,"is_veg":False,"is_popular":True,"is_bestseller":True,"is_signature":True,"description":"Slow-cooked mutton biryani","spice_level":"Medium","image_url":None,"source":"client"},
            {"item_name":"Veg Biryani","category":"Biryani","price":13.99,"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Mixed vegetable biryani","spice_level":"Mild","image_url":None,"source":"client"},
            {"item_name":"Hyderabadi Biryani","category":"Biryani","price":16.99,"is_veg":False,"is_popular":True,"is_bestseller":True,"is_signature":True,"description":"Authentic Hyderabadi dum biryani","spice_level":"Medium","image_url":None,"source":"client"},
            {"item_name":"Butter Chicken","category":"Curry","price":16.99,"is_veg":False,"is_popular":True,"is_bestseller":True,"is_signature":False,"description":"Rich and creamy butter chicken","spice_level":"Mild","image_url":None,"source":"client"},
            {"item_name":"Paneer Tikka Masala","category":"Curry","price":15.99,"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Grilled paneer in spiced gravy","spice_level":"Medium","image_url":None,"source":"client"},
            {"item_name":"Dal Makhani","category":"Curry","price":13.99,"is_veg":True,"is_popular":False,"is_bestseller":False,"is_signature":False,"description":"Creamy black lentil dal","spice_level":"Mild","image_url":None,"source":"client"},
            {"item_name":"Chicken Tikka","category":"Tandoori","price":14.99,"is_veg":False,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Tandoori chicken tikka","spice_level":"Medium","image_url":None,"source":"client"},
            {"item_name":"Tandoori Chicken","category":"Tandoori","price":15.99,"is_veg":False,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Half tandoori chicken","spice_level":"Hot","image_url":None,"source":"client"},
            {"item_name":"Garlic Naan","category":"Naan","price":3.99,"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Garlic flavored naan bread","spice_level":None,"image_url":None,"source":"client"},
            {"item_name":"Plain Naan","category":"Naan","price":2.99,"is_veg":True,"is_popular":False,"is_bestseller":False,"is_signature":False,"description":"Traditional naan","spice_level":None,"image_url":None,"source":"client"},
            {"item_name":"Samosa (2pc)","category":"Appetizer","price":6.99,"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Crispy potato samosas","spice_level":"Medium","image_url":None,"source":"client"},
            {"item_name":"Gulab Jamun","category":"Dessert","price":5.99,"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Sweet milk dumplings in syrup","spice_level":None,"image_url":None,"source":"client"},
            {"item_name":"Mango Lassi","category":"Drink","price":4.99,"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Yogurt-based mango drink","spice_level":None,"image_url":None,"source":"client"},
            {"item_name":"Family Feast","category":"Family Pack","price":49.99,"is_veg":False,"is_popular":False,"is_bestseller":False,"is_signature":False,"description":"2 Biryanis + 2 Curries + 4 Naans + Dessert","spice_level":"Medium","image_url":None,"source":"client"},
            {"item_name":"Lunch Thali","category":"Lunch Special","price":12.99,"is_veg":False,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Curry + Rice + Naan + Salad + Dessert","spice_level":"Medium","image_url":None,"source":"client"},
        ]

    def get_client_offers(self):
        """Return the client restaurant's current offers."""
        return [
            {"offer_type":"discount","title":"10% Off Online Orders","description":"Get 10% off when you order online","discount_percent":10,"discount_amount":None,"min_order_amount":20,"code":"ONLINE10","platform":"All","is_active":True,"source":"client"},
            {"offer_type":"combo","title":"Biryani Combo","description":"Any Biryani + Naan + Drink for $18.99","discount_percent":None,"discount_amount":None,"min_order_amount":None,"code":None,"platform":"All","is_active":True,"source":"client"},
            {"offer_type":"free_delivery","title":"Free Delivery $40+","description":"Free delivery on orders above $40","discount_percent":None,"discount_amount":5,"min_order_amount":40,"code":None,"platform":"UberEats","is_active":True,"source":"client"},
            {"offer_type":"loyalty","title":"Rewards Program","description":"Earn 1 point per $1 spent. 100 points = $10 off","discount_percent":None,"discount_amount":10,"min_order_amount":None,"code":None,"platform":"All","is_active":True,"source":"client"},
        ]

    # ── Private helpers ────────────────────────────────
    def _search_live(self, radius):
        """Attempt live search via Overpass API."""
        restaurants = []
        try:
            import requests
            # radius in miles to meters
            radius_m = radius * 1609.34
            q = f'[out:json];node["amenity"="restaurant"]["cuisine"~"indian",i](around:{radius_m}, {Config.CLIENT_LAT}, {Config.CLIENT_LNG});out body;'
            r = requests.post('https://overpass-api.de/api/interpreter', data=q, headers={'User-Agent': 'RestaurantApp/1.0'})
            data = r.json()
            for element in data.get('elements', []):
                lat = element.get('lat')
                lng = element.get('lon')
                tags = element.get('tags', {})
                name = tags.get('name')
                if not name or self._is_excluded(name):
                    continue
                address = f"{tags.get('addr:housenumber', '')} {tags.get('addr:street', '')}, {tags.get('addr:city', '')}".strip(', ')
                address = address if address else 'Location known, address unlisted'
                phone = tags.get('phone', tags.get('contact:phone', 'N/A'))
                
                dist = graphhopper_service.calculate_distance_from_client(lat, lng)
                distance_miles = dist['distance_miles']
                
                if distance_miles <= radius:
                    restaurants.append({
                        'name': name,
                        'address': address,
                        'phone': phone,
                        'latitude': lat,
                        'longitude': lng,
                        'distance_miles': distance_miles,
                        'rating': 4.0, # default since OSS doesn't provide rating
                        'total_reviews': 100,
                        'price_category': '$$',
                        'radius_group': graphhopper_service.get_radius_group(distance_miles),
                        'source': 'live_overpass',
                        'delivery_platforms': ["UberEats", "DoorDash"],
                        'cuisine_tags': ["Indian"]
                    })
        except Exception as e:
            print(f"[Competitor] Live search error: {e}")
        return restaurants

    def _is_excluded(self, name):
        """Check if a restaurant should be excluded from results."""
        excluded = ['bawarchi biryanis', 'bawarchi biryani']
        return name.lower().strip() in excluded

    def _is_client(self, name):
        return 'bawarchi' in name.lower()

competitor_service = CompetitorService()
