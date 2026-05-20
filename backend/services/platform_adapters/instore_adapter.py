"""
In-store adapter — wraps the existing competitor_service menu fetching
into the unified platform adapter interface.
"""

from services.platform_adapters.base_adapter import BasePlatformAdapter


class InstoreAdapter(BasePlatformAdapter):
    """Adapter for in-store / dine-in menu data (existing system)."""

    PLATFORM_NAME = 'instore'

    def __init__(self):
        from services.competitor_service import competitor_service
        self._competitor_service = competitor_service

    def fetch_menu(self, restaurant_name, location=None):
        """Get in-store menu from the existing competitor service."""
        try:
            # Check if this is the client restaurant
            client_name = self._competitor_service.client_restaurant.get('name', '')
            if restaurant_name.lower().strip() in client_name.lower():
                raw_menu = self._competitor_service.get_client_menu()
            else:
                raw_menu = self._find_competitor_menu(restaurant_name)

            if not raw_menu:
                return []

            return [self._normalize_item(item, source='instore') for item in raw_menu]
        except Exception as e:
            print(f"[InstoreAdapter] Error fetching menu for {restaurant_name}: {e}")
            return []

    def fetch_delivery_fees(self, restaurant_name, location=None):
        """In-store has no delivery fees — return zeros."""
        return {
            'delivery_fee': 0.0,
            'service_fee': 0.0,
            'surge_fee': 0.0,
            'tax_estimate': None,
            'free_delivery_threshold': 0.0,
            'min_order_amount': 0.0,
            'estimated_delivery_time': 'Dine-in',
        }

    def is_available(self):
        return True

    def _find_competitor_menu(self, restaurant_name):
        """Find a competitor's menu by name from the cached discovery data."""
        try:
            data = self._competitor_service.find_competitors()
            for r in data.get('restaurants', []):
                if r.get('name', '').lower().strip() == restaurant_name.lower().strip():
                    return self._competitor_service.get_restaurant_menu(r)
            # Fuzzy fallback
            for r in data.get('restaurants', []):
                if restaurant_name.lower() in r.get('name', '').lower():
                    return self._competitor_service.get_restaurant_menu(r)
        except Exception as e:
            print(f"[InstoreAdapter] Competitor lookup error: {e}")
        return None


instore_adapter = InstoreAdapter()
