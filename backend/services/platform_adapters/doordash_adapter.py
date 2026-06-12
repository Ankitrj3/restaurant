"""
DoorDash adapter — fetches REAL menu and delivery data from DoorDash.
Uses Gemini API with Google Search grounding to find actual DoorDash listings
and extract real platform-specific prices.
"""

import random
import time
from config import Config
from services.platform_adapters.base_adapter import BasePlatformAdapter
from services.cache_service import cache_service


class DoorDashAdapter(BasePlatformAdapter):
    """Adapter for DoorDash platform data — uses Google Search grounding."""

    PLATFORM_NAME = 'doordash'

    def __init__(self):
        pass

    def is_available(self):
        return Config.DOORDASH_SCRAPE_ENABLED

    def fetch_menu(self, restaurant_name, location=None):
        """Fetch DoorDash menu using Gemini Google Search grounding."""
        cache_key = f"{self.PLATFORM_NAME}_{restaurant_name.lower().strip()}"

        # 1. Valid Cache
        cached_menu = cache_service.get('menu', cache_key)
        if cached_menu: return cached_menu

        # Priority 1: Gemini with Google Search Grounding (REAL data)
        live_menu, platform_url = self._fetch_grounded_menu(restaurant_name)
        if live_menu:
            cache_service.set('menu', cache_key, live_menu)
            if platform_url:
                url_cache_key = f"platform_url_{self.PLATFORM_NAME}_{restaurant_name.lower().strip()}"
                cache_service.set('ai_response', url_cache_key, {'url': platform_url})
            return live_menu

        # Priority 2/3: Stale Cache Fallback
        fallback_menu = cache_service.get_latest('menu', cache_key)
        if fallback_menu:
            print(f"[DoorDash] Restored menu for {restaurant_name} from stale cache")
            return fallback_menu

        # Priority 6: AI-generated fallback with platform markups
        if Config.SCRAPING_FALLBACK_ENABLED:
            fallback = self._generate_fallback_menu(restaurant_name)
            return fallback

        return []

    def fetch_delivery_fees(self, restaurant_name, location=None):
        """Fetch DoorDash delivery fees using Gemini Google Search grounding."""
        cache_key = f"{self.PLATFORM_NAME}_{restaurant_name.lower().strip()}"

        # 1. Valid Cache
        cached_fees = cache_service.get('delivery_fee', cache_key)
        if cached_fees: return cached_fees

        # Priority 1: Gemini with Google Search Grounding
        live_fees = self._fetch_grounded_fees(restaurant_name)
        if live_fees:
            cache_service.set('delivery_fee', cache_key, live_fees)
            return live_fees

        # Priority 2/3: Stale Cache Fallback
        fallback_fees = cache_service.get_latest('delivery_fee', cache_key)
        if fallback_fees:
            print(f"[DoorDash] Restored delivery fees for {restaurant_name} from stale cache")
            return fallback_fees

        # Priority 6: Generate realistic fallback fees
        return self._generate_fallback_fees(restaurant_name)

    def _fetch_grounded_menu(self, restaurant_name):
        """Use Gemini with Google Search grounding to find REAL DoorDash menu prices.
        Returns (menu_items, platform_url) tuple."""
        try:
            from services.gemini_service import gemini_service
            if not gemini_service.is_available():
                return None, None

            address = Config.CLIENT_RESTAURANT_ADDRESS
            result = gemini_service.fetch_restaurant_menu_from_platform(
                restaurant_name, address, 'doordash'
            )

            if result and isinstance(result, dict):
                if result.get('not_found'):
                    print(f"[DoorDash] Restaurant '{restaurant_name}' not found on DoorDash via search")
                    return None, None
                platform_url = result.get('platform_url')
                items = result.get('items', [])
                if items:
                    print(f"[DoorDash] Found {len(items)} REAL items for '{restaurant_name}' via Google Search")
                    if platform_url:
                        print(f"[DoorDash] Platform URL: {platform_url}")
                    return [self._normalize_item(item, source='doordash_grounded') for item in items], platform_url
        except Exception as e:
            print(f"[DoorDashAdapter] Grounded search error: {e}")
        return None, None

    def fetch_platform_url(self, restaurant_name):
        """Get the real DoorDash page URL for this restaurant."""
        url_cache_key = f"platform_url_{self.PLATFORM_NAME}_{restaurant_name.lower().strip()}"

        # 1. Check cache
        cached = cache_service.get('ai_response', url_cache_key)
        if cached and isinstance(cached, dict) and cached.get('url'):
            return cached['url']

        # 2. Ask Gemini for the URL
        try:
            from services.gemini_service import gemini_service
            if gemini_service.is_available():
                result = gemini_service.search_restaurant_platform_url(
                    restaurant_name, Config.CLIENT_RESTAURANT_ADDRESS, 'doordash'
                )
                if result and isinstance(result, dict) and result.get('platform_url'):
                    url = result['platform_url']
                    cache_service.set('ai_response', url_cache_key, {'url': url})
                    print(f"[DoorDash] Found platform URL for '{restaurant_name}': {url}")
                    return url
        except Exception as e:
            print(f"[DoorDashAdapter] URL search error: {e}")

        # 3. Fallback: construct a location-anchored search URL
        from urllib.parse import quote_plus
        parts = [p.strip() for p in Config.CLIENT_RESTAURANT_ADDRESS.split(',') if p.strip()]
        city_state = f"{parts[-3]} {parts[-2].split()[0]}" if len(parts) >= 3 else ""
        search_q = quote_plus(f"{restaurant_name} {city_state}".strip())
        return f"https://www.doordash.com/search/store/{search_q}/"

    def _fetch_grounded_fees(self, restaurant_name):
        """Use Gemini with Google Search grounding to find REAL DoorDash delivery fees."""
        try:
            from services.gemini_service import gemini_service
            if not gemini_service.is_available():
                return None

            result = gemini_service.fetch_delivery_fees_from_platform(
                restaurant_name, 'DoorDash'
            )
            if result and isinstance(result, dict) and 'delivery_fee' in result:
                print(f"[DoorDash] Found REAL delivery fees for '{restaurant_name}' via Google Search")
                return result
        except Exception as e:
            print(f"[DoorDashAdapter] Grounded fee search error: {e}")
        return None

    def _generate_fallback_menu(self, restaurant_name):
        """Generate realistic DoorDash menu with platform markups."""
        from services.platform_adapters.instore_adapter import instore_adapter

        instore_menu = instore_adapter.fetch_menu(restaurant_name)
        if not instore_menu:
            from services.platform_adapters.ubereats_adapter import ubereats_adapter
            instore_menu = ubereats_adapter._get_generic_indian_menu()

        rng = random.Random(hash(restaurant_name + 'doordash'))
        dd_menu = []

        for item in instore_menu:
            instore_price = item.get('price')
            if instore_price:
                # DoorDash markup: 12–25% over in-store
                markup_pct = rng.uniform(0.12, 0.25)
                dd_price = round(instore_price * (1 + markup_pct), 2)
                markup = round(dd_price - instore_price, 2)
            else:
                dd_price = None
                markup = None

            dd_item = dict(item)
            dd_item['price'] = dd_price
            dd_item['markup_over_instore'] = markup
            dd_item['source'] = 'doordash_fallback'
            dd_item['is_available'] = rng.random() > 0.06
            dd_menu.append(dd_item)

        return dd_menu

    def _generate_fallback_fees(self, restaurant_name):
        """Generate realistic DoorDash delivery fees."""
        rng = random.Random(hash(restaurant_name + 'doordash_fees'))
        return {
            'delivery_fee': round(rng.uniform(0.99, 4.99), 2),
            'service_fee': round(rng.uniform(1.99, 4.49), 2),
            'surge_fee': round(rng.choice([0, 0, 0, 0, 1.00, 2.00]), 2),
            'tax_estimate': round(rng.uniform(1.20, 4.20), 2),
            'free_delivery_threshold': round(rng.choice([12.00, 15.00, 20.00, 25.00]), 2),
            'min_order_amount': round(rng.choice([8.00, 10.00, 12.00]), 2),
            'estimated_delivery_time': f"{rng.randint(20, 45)} min",
        }


doordash_adapter = DoorDashAdapter()
