"""
Competitor discovery service — orchestrates restaurant search across sources,
handles dynamic radius expansion, and deduplicates results.
"""

import json
import time
from config import Config
from services.graphhopper_service import graphhopper_service
from services.scraper_service import scraper_service
from services.gemini_service import gemini_service
from services.claude_service import claude_service
from services.cache_service import cache_service


# ── Realistic demo data (used when APIs/scraping unavailable) ──────────
DEMO_RESTAURANTS = [
    {"name":"Desi Dhaba (Kebab)","address":"Leander, TX","latitude":30.578,"longitude":-97.853,"rating":4.5,"total_reviews":120,"price_category":"$$","delivery_platforms":["UberEats"],"phone":"","cuisine_tags":["Indian","Kebab"]},
    {"name":"AnTenA Kitchen and Bar","address":"Leander, TX","latitude":30.560,"longitude":-97.820,"rating":4.4,"total_reviews":85,"price_category":"$$","delivery_platforms":["DoorDash"],"phone":"","cuisine_tags":["Indian","Andhra"]},
    {"name":"Veranda Bar & Restaurant","address":"Cedar Park, TX","latitude":30.520,"longitude":-97.800,"rating":4.2,"total_reviews":210,"price_category":"$$$","delivery_platforms":["UberEats","Grubhub"],"phone":"","cuisine_tags":["Indian","Fine Dining"]},
    {"name":"Desi Hangout","address":"Cedar Park, TX","latitude":30.530,"longitude":-97.810,"rating":4.6,"total_reviews":340,"price_category":"$","delivery_platforms":["DoorDash"],"phone":"","cuisine_tags":["Indian","Street Food"]},
    {"name":"Zest Indian Kitchen + Bar","address":"Round Rock, TX","latitude":30.508,"longitude":-97.678,"rating":4.3,"total_reviews":150,"price_category":"$$","delivery_platforms":["UberEats","DoorDash"],"phone":"","cuisine_tags":["Indian","Fusion"]},
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
        self._client_menu_cache = None
        self._client_menu_cache_ts = 0
        self._competitor_offers_cache = {}
        self._competitor_offers_cache_ts = {}

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
        Find nearby Indian restaurants using the 7-level Priority Chain.
        """
        if max_radius is None:
            max_radius = Config.SEARCH_RADII_MILES[-1]

        # 1. Try standard valid cache (Levels 1-3 handled by cache_service.get)
        cached_result = cache_service.get('discovery', max_radius)
        if cached_result and cached_result.get('competitors_found', 0) > 0:
            return cached_result

        print(f"[DEBUG] Cache miss/expired. Searching live for radius {max_radius}")
        
        # Priority 1: Live Platform (Gemini Search)
        all_restaurants = self._search_live(max_radius)

        if all_restaurants:
            print(f"[DEBUG] Live search returned {len(all_restaurants)} restaurants")
            result = {
                "search_radius_used": f"{max_radius} miles",
                "competitors_found": len(all_restaurants),
                "restaurants": sorted(all_restaurants, key=lambda x: x.get('distance_miles', 99)),
            }
            cache_service.set('discovery', max_radius, result)
            return result
            
        print("[Competitor] Gemini returned 0 results, attempting fallback chain")
        
        # Priority 2 & 3: Real PostgreSQL Cache / Local JSON Snapshots (ignoring TTL)
        fallback_cache = cache_service.get_latest('discovery', max_radius)
        if fallback_cache and fallback_cache.get('competitors_found', 0) > 0:
            print("[Competitor] Priority 2/3: Restored from stale cache")
            return fallback_cache
            
        # Priority 4 & 5 (AI Enrichment) not applicable for discovery without external search API
        
        # Priority 6: AI-generated Demo Data
        print("[Competitor] Priority 6: Using Demo Fallback Data")
        restaurants = []
        for demo in DEMO_RESTAURANTS:
            dist = graphhopper_service.calculate_distance_from_client(
                demo['latitude'], demo['longitude'])
            restaurants.append({
                **demo,
                'distance_miles': dist['distance_miles'],
                'radius_group': graphhopper_service.get_radius_group(dist['distance_miles']),
                'source': 'demo_fallback',
                'website_url': '',
            })
            
        result = {
            "search_radius_used": f"{max_radius} miles",
            "competitors_found": len(restaurants),
            "restaurants": sorted(restaurants, key=lambda x: x.get('distance_miles', 99)),
        }
        return result

    def get_restaurant_menu(self, restaurant):
        """Get menu following Priority Chain."""
        name = restaurant.get('name', '')
        cache_key = name.lower().strip()
        
        # 1. Valid Cache
        cached_menu = cache_service.get('menu', cache_key)
        if cached_menu: return cached_menu

        # Priority 1 & 4: Live Extraction + Gemini
        live_menu = self._get_restaurant_menu_live(restaurant)
        if live_menu:
            cache_service.set('menu', cache_key, live_menu)
            return live_menu
            
        # Priority 2 & 3: Stale Cache Fallback
        fallback_menu = cache_service.get_latest('menu', cache_key)
        if fallback_menu:
            print(f"[Competitor] Restored menu for {name} from stale cache")
            return fallback_menu
            
        # Priority 5: Claude AI Fallback Enrichment
        claude_menu = self._get_restaurant_menu_claude(restaurant)
        if claude_menu:
            print(f"[Competitor] Used Claude fallback for {name} menu")
            # Don't cache Claude to standard layer, let next run try Gemini again
            return claude_menu

        # Priority 6: Demo Fallback
        return self._get_restaurant_menu_demo(restaurant)

    def get_restaurant_offers(self, restaurant):
        """Get offers for a restaurant — live extraction or demo data."""
        name = restaurant.get('name', '')
        cache_key = name.lower().strip()
        now = time.time()
        ttl = Config.COMPETITOR_OFFERS_CACHE_SECONDS
        if cache_key in self._competitor_offers_cache:
            age = now - self._competitor_offers_cache_ts.get(cache_key, 0)
            if age < ttl:
                return self._competitor_offers_cache[cache_key]

        live_offers = self._get_restaurant_offers_live(restaurant)
        if live_offers:
            self._competitor_offers_cache[cache_key] = live_offers
            self._competitor_offers_cache_ts[cache_key] = now
            return live_offers

        return self._get_restaurant_offers_demo(restaurant)

    def get_client_menu(self):
        """Return the client restaurant's menu, with live scraping + caching."""
        now = time.time()
        cache_ttl = Config.CLIENT_MENU_CACHE_SECONDS
        if self._client_menu_cache and (now - self._client_menu_cache_ts) < cache_ttl:
            return self._client_menu_cache

        live_menu = self._get_client_menu_live()
        if live_menu:
            self._client_menu_cache = live_menu
            self._client_menu_cache_ts = now
            return live_menu

        # Fallback to static menu if live extraction fails
        return self._get_client_menu_fallback()

    def _get_client_menu_live(self):
        """Scrape the client website and extract menu using Claude."""
        menu_url = Config.CLIENT_MENU_URL
        if not menu_url:
            return None

        extracted = scraper_service.extract_menu_with_playwright(menu_url)
        if not extracted.get('success'):
            extracted = scraper_service.extract_menu_from_url(menu_url)
        if not extracted.get('success'):
            return None

        if not gemini_service.is_available():
            return None

        parsed = gemini_service.extract_menu_from_text(
            extracted.get('content', ''),
            Config.CLIENT_RESTAURANT_NAME,
        )
        items = parsed.get('items') if isinstance(parsed, dict) else None
        if not items:
            return None

        return self._normalize_menu_items(items, source='client_live')

    def _get_client_menu_fallback(self):
        """Fallback static menu if live scraping is unavailable."""
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
        """Fetch real competitor data dynamically using Gemini Search API, falling back to OSM."""
        print(f"[Competitor] Searching for Indian restaurants within {radius} miles using Gemini")
        restaurants = []
        try:
            location = f"{Config.CLIENT_LAT}, {Config.CLIENT_LNG}"
            data = gemini_service.search_nearby_restaurants(location, radius)
            
            if data and isinstance(data, list) and len(data) > 0:
                for place in data:
                    name = place.get('name')
                    if not name or self._is_excluded(name):
                        continue
                        
                    lat = place.get('latitude', 0.0)
                    lng = place.get('longitude', 0.0)
                    
                    dist = graphhopper_service.calculate_distance_from_client(lat, lng)
                    distance_miles = dist['distance_miles']
                    
                    if distance_miles <= radius:
                        restaurants.append({
                            'name': name,
                            'address': place.get('address', ''),
                            'phone': place.get('phone', ''),
                            'website_url': place.get('website_url', ''),
                            'latitude': lat,
                            'longitude': lng,
                            'distance_miles': distance_miles,
                            'rating': 4.0,
                            'total_reviews': 100,
                            'price_category': '$$',
                            'radius_group': graphhopper_service.get_radius_group(distance_miles),
                            'source': 'live_gemini',
                            'delivery_platforms': ["UberEats", "DoorDash"],
                            'cuisine_tags': place.get('cuisine_tags', ["Indian"])
                        })
                return restaurants
        except Exception as e:
            print(f"[Competitor] Live search error with Gemini: {e}")
            
        print(f"[Competitor] Gemini failed or returned 0 results. Falling back to OpenStreetMap (OSM) for radius {radius} miles.")
        try:
            from services.osm_service import osm_service
            data = osm_service.search_nearby_restaurants(Config.CLIENT_LAT, Config.CLIENT_LNG, radius)
            if data and isinstance(data, list):
                for place in data:
                    name = place.get('name')
                    if not name or self._is_excluded(name):
                        continue
                        
                    lat = place.get('latitude', 0.0)
                    lng = place.get('longitude', 0.0)
                    
                    dist = graphhopper_service.calculate_distance_from_client(lat, lng)
                    distance_miles = dist['distance_miles']
                    
                    if distance_miles <= radius:
                        restaurants.append({
                            'name': name,
                            'address': place.get('address', ''),
                            'phone': place.get('phone', ''),
                            'website_url': place.get('website_url', ''),
                            'latitude': lat,
                            'longitude': lng,
                            'distance_miles': distance_miles,
                            'rating': 4.0,  # OSM doesn't have ratings natively
                            'total_reviews': 50,
                            'price_category': '$$',
                            'radius_group': graphhopper_service.get_radius_group(distance_miles),
                            'source': 'live_osm',
                            'delivery_platforms': ["UberEats", "DoorDash"],
                            'cuisine_tags': place.get('cuisine_tags', ["Indian"])
                        })
        except Exception as e:
            print(f"[Competitor] OSM search error: {e}")
            
        return restaurants

    def _get_restaurant_menu_live(self, restaurant):
        """Scrape a competitor website and extract menu using Gemini."""
        website = self._get_restaurant_website(restaurant)
        if not website: return None

        extracted = scraper_service.extract_menu_with_playwright(website)
        if not extracted.get('success'):
            extracted = scraper_service.extract_menu_from_url(website)
        if not extracted.get('success'): return None
        if not gemini_service.is_available(): return None

        parsed = gemini_service.extract_menu_from_text(
            extracted.get('content', ''),
            restaurant.get('name', 'Unknown Restaurant'),
        )
        items = parsed.get('items') if isinstance(parsed, dict) else None
        if not items: return None
        return self._normalize_menu_items(items, source='competitor_live')

    def _get_restaurant_menu_claude(self, restaurant):
        """Priority 5: Scrape website and extract using Claude Fallback."""
        website = self._get_restaurant_website(restaurant)
        if not website: return None
        if not claude_service.is_available(): return None
        
        extracted = scraper_service.extract_menu_with_playwright(website)
        if not extracted.get('success'):
            extracted = scraper_service.extract_menu_from_url(website)
        if not extracted.get('success'): return None
        
        parsed = claude_service.extract_menu_from_text(
            extracted.get('content', ''),
            restaurant.get('name', 'Unknown Restaurant'),
        )
        items = parsed.get('items') if isinstance(parsed, dict) else None
        if not items: return None
        return self._normalize_menu_items(items, source='claude_fallback')

    def _get_restaurant_offers_live(self, restaurant):
        """Scrape a competitor website and extract offers using Claude."""
        website = self._get_restaurant_website(restaurant)
        if not website:
            return None

        extracted = scraper_service.extract_offers_from_page(website)
        if not extracted.get('success'):
            return None

        if not gemini_service.is_available():
            return None

        parsed = gemini_service.extract_offers_from_text(
            '\n'.join(extracted.get('raw_offers', [])),
            restaurant.get('name', 'Unknown Restaurant'),
        )
        offers = parsed.get('offers') if isinstance(parsed, dict) else None
        if not offers:
            return None

        return self._normalize_offers(offers, source='competitor_live')

    def _get_restaurant_website(self, restaurant):
        """Get website from OSM tags or ask AI to infer it."""
        website = restaurant.get('website_url')
        if self._is_valid_url(website):
            return website

        if not Config.COMPETITOR_WEBSITE_GUESS_ENABLED:
            return None

        guess = None
        if gemini_service.is_available():
            guess = gemini_service.infer_restaurant_website(
                restaurant.get('name', ''),
                restaurant.get('address', ''),
            )
            
        if (not guess or not self._is_valid_url(guess.get('website_url'))) and claude_service.is_available():
            print(f"[Competitor] Gemini website inference failed/skipped for {restaurant.get('name')}. Trying Claude.")
            claude_guess = claude_service.infer_restaurant_website(
                restaurant.get('name', ''),
                restaurant.get('address', ''),
            )
            if claude_guess and isinstance(claude_guess, dict):
                guess = claude_guess
                
        website = guess.get('website_url') if isinstance(guess, dict) else None
        if self._is_valid_url(website):
            return website
        return None

    def _is_valid_url(self, url):
        if not url or not isinstance(url, str):
            return False
        return url.startswith('http://') or url.startswith('https://')

    def _normalize_menu_items(self, items, source):
        """Normalize menu items into the UI schema."""
        normalized = []
        for item in items:
            name = item.get('item_name') or item.get('name')
            if not name:
                continue
            price = item.get('price')
            if isinstance(price, str):
                price = price.replace('$', '').strip()
                try:
                    price = float(price)
                except ValueError:
                    price = None
            normalized.append({
                "item_name": name,
                "category": item.get('category') or "Other",
                "price": price,
                "is_veg": bool(item.get('is_veg')),
                "is_popular": bool(item.get('is_popular')),
                "is_bestseller": bool(item.get('is_bestseller')),
                "is_signature": bool(item.get('is_signature')),
                "description": item.get('description'),
                "spice_level": item.get('spice_level'),
                "image_url": None,
                "source": source,
            })
        return normalized

    def _normalize_offers(self, offers, source):
        """Normalize offers into the UI schema."""
        normalized = []
        for offer in offers:
            title = offer.get('title')
            if not title:
                continue
            normalized.append({
                "offer_type": offer.get('offer_type') or "discount",
                "title": title,
                "description": offer.get('description') or '',
                "discount_percent": offer.get('discount_percent'),
                "discount_amount": offer.get('discount_amount'),
                "min_order_amount": offer.get('min_order_amount'),
                "code": offer.get('code'),
                "platform": offer.get('platform') or "Website",
                "is_active": True,
                "source": source,
            })
        return normalized

    def _get_restaurant_menu_demo(self, restaurant):
        """Demo menu used when live data is unavailable."""
        import random
        base = list(DEMO_MENUS["default"])
        seed = hash(restaurant.get('name', ''))
        rng = random.Random(seed)
        menu = []
        for item in base:
            item_copy = dict(item)
            if item_copy['price']:
                factor = rng.uniform(0.8, 1.25)
                item_copy['price'] = round(item_copy['price'] * factor, 2)
            menu.append(item_copy)
        if rng.random() > 0.5:
            menu.append({"item_name":"Goat Curry","category":"Curry","price":round(rng.uniform(15,20),2),"is_veg":False,"is_popular":False,"is_bestseller":False,"is_signature":True,"description":"Slow-cooked goat curry","spice_level":"Hot","image_url":None,"source":"demo"})
        if rng.random() > 0.4:
            menu.append({"item_name":"Chole Bhature","category":"Appetizer","price":round(rng.uniform(10,14),2),"is_veg":True,"is_popular":True,"is_bestseller":False,"is_signature":False,"description":"Chickpea curry with fried bread","spice_level":"Medium","image_url":None,"source":"demo"})
        return menu

    def _get_restaurant_offers_demo(self, restaurant):
        """Demo offers used when live data is unavailable."""
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

    def _is_excluded(self, name):
        """Check if a restaurant should be excluded from results."""
        excluded = [
            'bawarchi biryanis',
            'bawarchi biryani',
            'bawarchi indian cuisine & bar leander',
        ]
        return name.lower().strip() in excluded

    def _is_client(self, name):
        return 'bawarchi' in name.lower()

competitor_service = CompetitorService()
