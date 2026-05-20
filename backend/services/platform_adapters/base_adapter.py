"""
Abstract base class for platform adapters.
All platform-specific adapters (UberEats, DoorDash, Grubhub, Instore)
inherit from this and implement the fetch methods.
"""

from abc import ABC, abstractmethod


class BasePlatformAdapter(ABC):
    """Abstract interface for platform data fetching."""

    PLATFORM_NAME = 'unknown'

    @abstractmethod
    def fetch_menu(self, restaurant_name, location=None):
        """
        Fetch menu items for a restaurant on this platform.
        Returns list of normalized items:
        [{ item_name, category, price, is_available, is_veg, description, source }]
        """
        pass

    @abstractmethod
    def fetch_delivery_fees(self, restaurant_name, location=None):
        """
        Fetch delivery fee structure for a restaurant.
        Returns dict:
        { delivery_fee, service_fee, surge_fee, tax_estimate,
          free_delivery_threshold, min_order_amount, estimated_delivery_time }
        """
        pass

    @abstractmethod
    def is_available(self):
        """Check if this platform adapter is enabled and functional."""
        pass

    def _safe_float(self, val):
        """Safely convert a value to float."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            cleaned = val.replace('$', '').replace(',', '').strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    def _normalize_item(self, raw_item, source=None):
        """Normalize a raw menu item dict into standard schema."""
        from services.matching_service import matching_service
        name = raw_item.get('item_name') or raw_item.get('name') or ''
        return {
            'item_name': name,
            'item_name_normalized': matching_service.normalize_name(name),
            'category': raw_item.get('category') or None,
            'price': self._safe_float(raw_item.get('price')),
            'is_available': raw_item.get('is_available', True),
            'is_veg': bool(raw_item.get('is_veg', False)),
            'description': raw_item.get('description'),
            'source': source or self.PLATFORM_NAME,
        }

    def _empty_delivery_fees(self):
        """Return empty delivery fee structure."""
        return {
            'delivery_fee': None,
            'service_fee': None,
            'surge_fee': None,
            'tax_estimate': None,
            'free_delivery_threshold': None,
            'min_order_amount': None,
            'estimated_delivery_time': None,
        }
