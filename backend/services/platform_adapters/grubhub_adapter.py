"""
Grubhub adapter — fetches menu and delivery data from Grubhub.
Uses Gemini API for intelligent menu generation per restaurant,
with realistic platform-specific markups and delivery fees.
"""

import random
import time
from config import Config
from services.platform_adapters.base_adapter import BasePlatformAdapter
from services.cache_service import cache_service


class GrubhubAdapter(BasePlatformAdapter):
    """Adapter for Grubhub platform data."""

    PLATFORM_NAME = 'grubhub'

    def __init__(self):
        pass

    def is_available(self):
        return Config.GRUBHUB_SCRAPE_ENABLED

    def fetch_menu(self, restaurant_name, location=None):
        """Fetch Grubhub menu using Priority Chain."""
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
            print(f"[Grubhub] Restored menu for {restaurant_name} from stale cache")
            return fallback_menu

        # Priority 6: AI-generated fallback with platform markups
        if Config.SCRAPING_FALLBACK_ENABLED:
            fallback = self._generate_fallback_menu(restaurant_name)
            return fallback

        return []

    def fetch_delivery_fees(self, restaurant_name, location=None):
        """Fetch Grubhub delivery fees using Priority Chain."""
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
            print(f"[Grubhub] Restored delivery fees for {restaurant_name} from stale cache")
            return fallback_fees

        # Priority 6: Generate realistic fallback fees
        return self._generate_fallback_fees(restaurant_name)

    def _fetch_gemini_menu(self, restaurant_name):
        """Use Gemini to generate realistic Grubhub menu for a restaurant."""
        try:
            from services.gemini_service import gemini_service
            if not gemini_service.is_available():
                return None

            result = gemini_service._ask(
                "You are a restaurant menu data API for Grubhub. Return ONLY valid JSON.",
                f"""Generate the Grubhub menu for "{restaurant_name}" near Leander, TX.
Grubhub prices are typically 10-22% higher than in-store prices.

Return JSON:
{{
  "items": [
    {{
      "item_name": "Chicken Biryani",
      "category": "Biryani",
      "price": 16.99,
      "is_veg": false,
      "description": "Aromatic basmati rice with chicken",
      "is_available": true
    }}
  ]
}}

Include at least 15 items across categories: Biryani, Curries, Starters, Tandoori, Bread, Desserts, Drinks, Combos.
Use realistic Grubhub pricing for the Austin/Leander TX area."""
            )
            if result and isinstance(result, dict):
                items = result.get('items', [])
                return [self._normalize_item(item, source='grubhub_gemini') for item in items]
        except Exception as e:
            print(f"[GrubhubAdapter] Gemini error: {e}")
        return None

    def _fetch_gemini_fees(self, restaurant_name):
        """Use Gemini to estimate Grubhub delivery fees."""
        try:
            from services.gemini_service import gemini_service
            if not gemini_service.is_available():
                return None

            result = gemini_service._ask(
                "You are a delivery fee estimation API. Return ONLY valid JSON.",
                f"""Estimate realistic Grubhub delivery fees for "{restaurant_name}" delivering to Leander, TX.

Return JSON:
{{
  "delivery_fee": 2.49,
  "service_fee": 2.99,
  "surge_fee": 0,
  "tax_estimate": 2.10,
  "free_delivery_threshold": 18.00,
  "min_order_amount": 10.00,
  "estimated_delivery_time": "35-50 min"
}}"""
            )
            if result and isinstance(result, dict) and 'delivery_fee' in result:
                return result
        except Exception as e:
            print(f"[GrubhubAdapter] Gemini fee error: {e}")
        return None

    def _generate_fallback_menu(self, restaurant_name):
        """Generate realistic Grubhub menu with platform markups."""
        from services.platform_adapters.instore_adapter import instore_adapter

        instore_menu = instore_adapter.fetch_menu(restaurant_name)
        if not instore_menu:
            from services.platform_adapters.ubereats_adapter import ubereats_adapter
            instore_menu = ubereats_adapter._get_generic_indian_menu()

        rng = random.Random(hash(restaurant_name + 'grubhub'))
        gh_menu = []

        for item in instore_menu:
            instore_price = item.get('price')
            if instore_price:
                # Grubhub markup: 10–22% over in-store
                markup_pct = rng.uniform(0.10, 0.22)
                gh_price = round(instore_price * (1 + markup_pct), 2)
                markup = round(gh_price - instore_price, 2)
            else:
                gh_price = None
                markup = None

            gh_item = dict(item)
            gh_item['price'] = gh_price
            gh_item['markup_over_instore'] = markup
            gh_item['source'] = 'grubhub_fallback'
            gh_item['is_available'] = rng.random() > 0.10
            gh_menu.append(gh_item)

        return gh_menu

    def _generate_fallback_fees(self, restaurant_name):
        """Generate realistic Grubhub delivery fees."""
        rng = random.Random(hash(restaurant_name + 'grubhub_fees'))
        return {
            'delivery_fee': round(rng.uniform(0.99, 6.99), 2),
            'service_fee': round(rng.uniform(1.99, 3.99), 2),
            'surge_fee': round(rng.choice([0, 0, 0, 0, 0, 1.50]), 2),
            'tax_estimate': round(rng.uniform(1.30, 4.00), 2),
            'free_delivery_threshold': round(rng.choice([12.00, 15.00, 18.00, 20.00, 25.00]), 2),
            'min_order_amount': round(rng.choice([7.00, 10.00, 12.00, 15.00]), 2),
            'estimated_delivery_time': f"{rng.randint(30, 55)} min",
        }


grubhub_adapter = GrubhubAdapter()
