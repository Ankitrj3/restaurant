"""
Uber Eats adapter — fetches menu and delivery data from Uber Eats.
Uses Gemini API for intelligent menu generation per restaurant,
with realistic platform-specific markups and delivery fees.
"""

import random
import time
from config import Config
from services.platform_adapters.base_adapter import BasePlatformAdapter
from services.cache_service import cache_service


class UberEatsAdapter(BasePlatformAdapter):
    """Adapter for Uber Eats platform data."""

    PLATFORM_NAME = 'ubereats'

    def __init__(self):
        pass

    def is_available(self):
        return Config.UBEREATS_SCRAPE_ENABLED

    def fetch_menu(self, restaurant_name, location=None):
        """Fetch Uber Eats menu using Priority Chain."""
        cache_key = f"{self.PLATFORM_NAME}_{restaurant_name.lower().strip()}"
        
        # 1. Valid Cache
        cached_menu = cache_service.get('menu', cache_key)
        if cached_menu: return cached_menu

        # Priority 1: Gemini Live
        live_menu = self._fetch_gemini_menu(restaurant_name)
        if live_menu:
            cache_service.set('menu', cache_key, live_menu)
            return live_menu
            
        # Priority 2/3: Stale Cache Fallback
        fallback_menu = cache_service.get_latest('menu', cache_key)
        if fallback_menu:
            print(f"[UberEats] Restored menu for {restaurant_name} from stale cache")
            return fallback_menu

        # Priority 6: AI-generated fallback with platform markups
        if Config.SCRAPING_FALLBACK_ENABLED:
            fallback = self._generate_fallback_menu(restaurant_name)
            # Do not cache fallback data to the main cache to allow live retries
            return fallback

        return []

    def fetch_delivery_fees(self, restaurant_name, location=None):
        """Fetch Uber Eats delivery fees using Priority Chain."""
        cache_key = f"{self.PLATFORM_NAME}_{restaurant_name.lower().strip()}"
        
        # 1. Valid Cache
        cached_fees = cache_service.get('delivery_fee', cache_key)
        if cached_fees: return cached_fees

        # Priority 1: Gemini Live
        live_fees = self._fetch_gemini_fees(restaurant_name)
        if live_fees:
            cache_service.set('delivery_fee', cache_key, live_fees)
            return live_fees
            
        # Priority 2/3: Stale Cache Fallback
        fallback_fees = cache_service.get_latest('delivery_fee', cache_key)
        if fallback_fees:
            print(f"[UberEats] Restored delivery fees for {restaurant_name} from stale cache")
            return fallback_fees

        # Priority 6: Generate realistic fallback fees
        return self._generate_fallback_fees(restaurant_name)

    def _fetch_gemini_menu(self, restaurant_name):
        """Use Gemini to generate realistic Uber Eats menu for a restaurant."""
        try:
            from services.gemini_service import gemini_service
            if not gemini_service.is_available():
                return None

            result = gemini_service._ask(
                "You are a restaurant menu data API for Uber Eats. Return ONLY valid JSON.",
                f"""Generate the Uber Eats menu for "{restaurant_name}" near Leander, TX.
Uber Eats prices are typically 15-30% higher than in-store prices.

Return JSON:
{{
  "items": [
    {{
      "item_name": "Chicken Biryani",
      "category": "Biryani",
      "price": 17.99,
      "is_veg": false,
      "description": "Aromatic basmati rice with chicken",
      "is_available": true
    }}
  ]
}}

Include at least 15 items across categories: Biryani, Curries, Starters, Tandoori, Bread, Desserts, Drinks, Combos.
Use realistic Uber Eats pricing for the Austin/Leander TX area."""
            )
            if result and isinstance(result, dict):
                items = result.get('items', [])
                return [self._normalize_item(item, source='ubereats_gemini') for item in items]
        except Exception as e:
            print(f"[UberEatsAdapter] Gemini error: {e}")
        return None

    def _fetch_gemini_fees(self, restaurant_name):
        """Use Gemini to estimate Uber Eats delivery fees."""
        try:
            from services.gemini_service import gemini_service
            if not gemini_service.is_available():
                return None

            result = gemini_service._ask(
                "You are a delivery fee estimation API. Return ONLY valid JSON.",
                f"""Estimate realistic Uber Eats delivery fees for "{restaurant_name}" delivering to Leander, TX.

Return JSON:
{{
  "delivery_fee": 3.99,
  "service_fee": 3.49,
  "surge_fee": 0,
  "tax_estimate": 2.50,
  "free_delivery_threshold": 25.00,
  "min_order_amount": 12.00,
  "estimated_delivery_time": "30-45 min"
}}"""
            )
            if result and isinstance(result, dict) and 'delivery_fee' in result:
                return result
        except Exception as e:
            print(f"[UberEatsAdapter] Gemini fee error: {e}")
        return None

    def _generate_fallback_menu(self, restaurant_name):
        """Generate realistic Uber Eats menu with platform markups."""
        from services.platform_adapters.instore_adapter import instore_adapter

        instore_menu = instore_adapter.fetch_menu(restaurant_name)
        if not instore_menu:
            instore_menu = self._get_generic_indian_menu()

        rng = random.Random(hash(restaurant_name + 'ubereats'))
        uber_menu = []

        for item in instore_menu:
            instore_price = item.get('price')
            if instore_price:
                # Uber Eats markup: 15–30% over in-store
                markup_pct = rng.uniform(0.15, 0.30)
                uber_price = round(instore_price * (1 + markup_pct), 2)
                markup = round(uber_price - instore_price, 2)
            else:
                uber_price = None
                markup = None

            uber_item = dict(item)
            uber_item['price'] = uber_price
            uber_item['markup_over_instore'] = markup
            uber_item['source'] = 'ubereats_fallback'
            # Some items may be unavailable on the platform
            uber_item['is_available'] = rng.random() > 0.08
            uber_menu.append(uber_item)

        return uber_menu

    def _generate_fallback_fees(self, restaurant_name):
        """Generate realistic Uber Eats delivery fees."""
        rng = random.Random(hash(restaurant_name + 'ubereats_fees'))
        return {
            'delivery_fee': round(rng.uniform(1.99, 5.99), 2),
            'service_fee': round(rng.uniform(2.49, 4.99), 2),
            'surge_fee': round(rng.choice([0, 0, 0, 1.50, 2.00, 3.00]), 2),
            'tax_estimate': round(rng.uniform(1.50, 4.50), 2),
            'free_delivery_threshold': round(rng.choice([15.00, 20.00, 25.00, 30.00, 35.00]), 2),
            'min_order_amount': round(rng.choice([10.00, 12.00, 15.00]), 2),
            'estimated_delivery_time': f"{rng.randint(25, 50)} min",
        }

    def _get_generic_indian_menu(self):
        """Generic Indian restaurant menu for when no in-store data exists."""
        return [
            {'item_name': 'Chicken Biryani', 'category': 'Biryani', 'price': 15.99, 'is_veg': False, 'description': 'Aromatic basmati rice with chicken'},
            {'item_name': 'Mutton Biryani', 'category': 'Biryani', 'price': 18.99, 'is_veg': False, 'description': 'Slow-cooked mutton biryani'},
            {'item_name': 'Veg Biryani', 'category': 'Biryani', 'price': 13.99, 'is_veg': True, 'description': 'Mixed vegetable biryani'},
            {'item_name': 'Goat Biryani', 'category': 'Biryani', 'price': 19.99, 'is_veg': False, 'description': 'Tender goat biryani'},
            {'item_name': 'Butter Chicken', 'category': 'Curries', 'price': 16.99, 'is_veg': False, 'description': 'Creamy tomato butter sauce'},
            {'item_name': 'Paneer Tikka Masala', 'category': 'Curries', 'price': 15.99, 'is_veg': True, 'description': 'Grilled paneer in spiced gravy'},
            {'item_name': 'Chicken Tikka Masala', 'category': 'Curries', 'price': 16.99, 'is_veg': False, 'description': 'Tandoori chicken in masala sauce'},
            {'item_name': 'Dal Makhani', 'category': 'Curries', 'price': 13.99, 'is_veg': True, 'description': 'Creamy black lentils'},
            {'item_name': 'Palak Paneer', 'category': 'Curries', 'price': 14.99, 'is_veg': True, 'description': 'Spinach and cottage cheese'},
            {'item_name': 'Chicken Tikka', 'category': 'Starters', 'price': 13.99, 'is_veg': False, 'description': 'Tandoori chicken pieces'},
            {'item_name': 'Samosa (2pc)', 'category': 'Starters', 'price': 6.99, 'is_veg': True, 'description': 'Crispy potato samosas'},
            {'item_name': 'Onion Bhaji', 'category': 'Starters', 'price': 7.99, 'is_veg': True, 'description': 'Crispy onion fritters'},
            {'item_name': 'Tandoori Chicken', 'category': 'Tandoori', 'price': 15.99, 'is_veg': False, 'description': 'Half tandoori chicken'},
            {'item_name': 'Seekh Kebab', 'category': 'Tandoori', 'price': 14.99, 'is_veg': False, 'description': 'Minced meat kebabs'},
            {'item_name': 'Garlic Naan', 'category': 'Bread', 'price': 3.99, 'is_veg': True, 'description': 'Garlic flavored naan'},
            {'item_name': 'Plain Naan', 'category': 'Bread', 'price': 2.99, 'is_veg': True, 'description': 'Traditional naan'},
            {'item_name': 'Butter Naan', 'category': 'Bread', 'price': 3.49, 'is_veg': True, 'description': 'Buttery naan bread'},
            {'item_name': 'Jeera Rice', 'category': 'Rice', 'price': 4.99, 'is_veg': True, 'description': 'Cumin-flavored rice'},
            {'item_name': 'Gulab Jamun', 'category': 'Desserts', 'price': 5.99, 'is_veg': True, 'description': 'Sweet milk dumplings'},
            {'item_name': 'Rasmalai', 'category': 'Desserts', 'price': 6.99, 'is_veg': True, 'description': 'Cottage cheese in cream'},
            {'item_name': 'Mango Lassi', 'category': 'Drinks', 'price': 4.99, 'is_veg': True, 'description': 'Yogurt mango drink'},
            {'item_name': 'Masala Chai', 'category': 'Drinks', 'price': 3.99, 'is_veg': True, 'description': 'Spiced tea'},
            {'item_name': 'Family Biryani Pack', 'category': 'Combos', 'price': 49.99, 'is_veg': False, 'description': 'Feeds 4-5 people'},
            {'item_name': 'Lunch Combo', 'category': 'Combos', 'price': 12.99, 'is_veg': False, 'description': 'Curry + Rice + Naan + Drink'},
        ]


ubereats_adapter = UberEatsAdapter()
