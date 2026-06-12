"""
Platform orchestrator service — coordinates all platform adapters,
aggregates cross-platform data, and provides unified comparison APIs.
"""

import time
from config import Config
from services.matching_service import matching_service


# Supported platforms
PLATFORMS = ['instore', 'ubereats', 'doordash', 'grubhub']
PLATFORM_LABELS = {
    'instore': 'In-Store',
    'ubereats': 'Uber Eats',
    'doordash': 'DoorDash',
    'grubhub': 'Grubhub',
}

# Supported categories
STANDARD_CATEGORIES = [
    'Biryani', 'Curries', 'Starters', 'Desserts', 'Tandoori',
    'Samosa', 'Drinks', 'Bread', 'Rice', 'Combos', 'Veg', 'Non-Veg',
]


def _get_adapter(platform):
    """Lazy-load platform adapter to avoid circular imports."""
    if platform == 'instore':
        from services.platform_adapters.instore_adapter import instore_adapter
        return instore_adapter
    elif platform == 'ubereats':
        from services.platform_adapters.ubereats_adapter import ubereats_adapter
        return ubereats_adapter
    elif platform == 'doordash':
        from services.platform_adapters.doordash_adapter import doordash_adapter
        return doordash_adapter
    elif platform == 'grubhub':
        from services.platform_adapters.grubhub_adapter import grubhub_adapter
        return grubhub_adapter
    return None


class PlatformService:
    """Orchestrator for multi-platform restaurant data aggregation."""

    def __init__(self):
        self._aggregated_cache = {}
        self._cache_ts = {}

    def get_restaurant_names(self):
        """Get list of all known restaurants (client + competitors)."""
        try:
            from services.competitor_service import competitor_service
            client_name = competitor_service.client_restaurant.get('name', '')
            data = competitor_service.find_competitors()
            names = [client_name]
            for r in data.get('restaurants', []):
                names.append(r.get('name', ''))
            return [n for n in names if n]
        except Exception:
            return [Config.CLIENT_RESTAURANT_NAME]

    def get_all_categories(self, restaurant_name=None):
        """Get all categories — union of standard + dynamic from data."""
        categories = set(STANDARD_CATEGORIES)

        if restaurant_name:
            for platform in PLATFORMS:
                adapter = _get_adapter(platform)
                if adapter and adapter.is_available():
                    try:
                        menu = adapter.fetch_menu(restaurant_name)
                        for item in menu:
                            cat = item.get('category')
                            if cat and cat not in ('Other', 'Unknown', None):
                                categories.add(cat)
                    except Exception:
                        pass

        return sorted(categories)

    def get_platform_menu(self, restaurant_name, platform):
        """Fetch menu for a specific restaurant on a specific platform."""
        adapter = _get_adapter(platform)
        if not adapter or not adapter.is_available():
            return []
        try:
            return adapter.fetch_menu(restaurant_name)
        except Exception as e:
            print(f"[PlatformService] Error fetching {platform} menu for {restaurant_name}: {e}")
            return []

    def get_platform_delivery_fees(self, restaurant_name, platform):
        """Fetch delivery fees for a specific restaurant on a specific platform."""
        adapter = _get_adapter(platform)
        if not adapter or not adapter.is_available():
            return self._empty_fees()
        try:
            return adapter.fetch_delivery_fees(restaurant_name)
        except Exception as e:
            print(f"[PlatformService] Error fetching {platform} fees for {restaurant_name}: {e}")
            return self._empty_fees()

    def get_all_delivery_fees(self, restaurant_names=None):
        """Get delivery fees for all restaurants across all platforms."""
        if restaurant_names is None:
            restaurant_names = self.get_restaurant_names()

        result = []
        for rname in restaurant_names:
            entry = {'restaurant_name': rname, 'platforms': {}}
            for platform in PLATFORMS:
                fees = self.get_platform_delivery_fees(rname, platform)
                entry['platforms'][platform] = fees
            result.append(entry)
        return result

    def get_free_delivery_thresholds(self, restaurant_names=None):
        """Get free delivery thresholds for all restaurants across platforms."""
        if restaurant_names is None:
            restaurant_names = self.get_restaurant_names()

        result = []
        for rname in restaurant_names:
            entry = {'restaurant_name': rname, 'thresholds': {}}
            for platform in PLATFORMS:
                fees = self.get_platform_delivery_fees(rname, platform)
                entry['thresholds'][platform] = fees.get('free_delivery_threshold')
            result.append(entry)
        return result

    def compare_instore(self, competitor_name=None):
        """
        Compare Bawarchi in-store prices vs competitor in-store prices.
        If competitor_name is None, compare against all competitors.
        """
        from services.competitor_service import competitor_service
        client_name = competitor_service.client_restaurant.get('name', '')
        client_menu = self.get_platform_menu(client_name, 'instore')

        if competitor_name:
            comp_menu = self.get_platform_menu(competitor_name, 'instore')
            return self._build_price_comparison(
                client_name, client_menu, competitor_name, comp_menu, 'instore'
            )

        # Full market comparison
        data = competitor_service.find_competitors()
        results = []
        for r in data.get('restaurants', []):
            comp_name = r.get('name', '')
            comp_menu = self.get_platform_menu(comp_name, 'instore')
            comp = self._build_price_comparison(
                client_name, client_menu, comp_name, comp_menu, 'instore'
            )
            results.append(comp)
        return results

    def compare_platform(self, platform, competitor_name=None):
        """Compare Bawarchi platform prices vs competitor platform prices."""
        from services.competitor_service import competitor_service
        client_name = competitor_service.client_restaurant.get('name', '')
        client_menu = self.get_platform_menu(client_name, platform)
        client_instore = self.get_platform_menu(client_name, 'instore')

        if competitor_name:
            comp_menu = self.get_platform_menu(competitor_name, platform)
            comp_instore = self.get_platform_menu(competitor_name, 'instore')
            return self._build_platform_comparison(
                client_name, client_menu, client_instore,
                competitor_name, comp_menu, comp_instore, platform
            )

        data = competitor_service.find_competitors()
        results = []
        for r in data.get('restaurants', []):
            comp_name = r.get('name', '')
            comp_menu = self.get_platform_menu(comp_name, platform)
            comp_instore = self.get_platform_menu(comp_name, 'instore')
            comp = self._build_platform_comparison(
                client_name, client_menu, client_instore,
                comp_name, comp_menu, comp_instore, platform
            )
            results.append(comp)
        return results

    def compare_platform_to_platform(self, restaurant_name=None):
        """Compare prices across platforms for the same restaurant."""
        from services.competitor_service import competitor_service
        if not restaurant_name:
            restaurant_name = competitor_service.client_restaurant.get('name', '')

        platform_menus = {}
        for platform in PLATFORMS:
            platform_menus[platform] = self.get_platform_menu(restaurant_name, platform)

        # Build unified item list using fuzzy matching
        all_items = {}
        for platform, menu in platform_menus.items():
            for item in menu:
                name = item.get('item_name', '')
                norm = matching_service.normalize_name(name)
                matched_key = None
                for existing_key in all_items:
                    if matching_service.similarity_score(name, existing_key) >= Config.FUZZY_MATCH_THRESHOLD:
                        matched_key = existing_key
                        break
                key = matched_key or name
                if key not in all_items:
                    all_items[key] = {
                        'item_name': name,
                        'category': item.get('category'),
                        'is_veg': item.get('is_veg'),
                        'platforms': {},
                    }
                all_items[key]['platforms'][platform] = {
                    'price': item.get('price'),
                    'is_available': item.get('is_available', True),
                }

        # Find cheapest platform per item
        comparison = []
        for key, data in all_items.items():
            prices = {}
            for p, info in data['platforms'].items():
                if info.get('price') is not None and info.get('is_available', True):
                    prices[p] = info['price']

            cheapest = min(prices, key=prices.get) if prices else None

            comparison.append({
                'item_name': data['item_name'],
                'category': data.get('category'),
                'is_veg': data.get('is_veg'),
                'instore_price': data['platforms'].get('instore', {}).get('price'),
                'ubereats_price': data['platforms'].get('ubereats', {}).get('price'),
                'doordash_price': data['platforms'].get('doordash', {}).get('price'),
                'grubhub_price': data['platforms'].get('grubhub', {}).get('price'),
                'cheapest_platform': cheapest,
            })

        return {
            'restaurant_name': restaurant_name,
            'items': comparison,
            'platforms': PLATFORMS,
        }

    def compare_restaurant_to_restaurant(self, restaurant_names, platform='instore'):
        """Compare multiple restaurants on the same platform."""
        restaurant_menus = {}
        for rname in restaurant_names:
            restaurant_menus[rname] = self.get_platform_menu(rname, platform)

        # Build unified item list
        all_items = {}
        for rname, menu in restaurant_menus.items():
            for item in menu:
                name = item.get('item_name', '')
                matched_key = None
                for existing_key in all_items:
                    if matching_service.similarity_score(name, existing_key) >= Config.FUZZY_MATCH_THRESHOLD:
                        matched_key = existing_key
                        break
                key = matched_key or name
                if key not in all_items:
                    all_items[key] = {
                        'item_name': name,
                        'category': item.get('category'),
                        'is_veg': item.get('is_veg'),
                        'restaurants': {},
                    }
                all_items[key]['restaurants'][rname] = {
                    'price': item.get('price'),
                    'is_available': item.get('is_available', True),
                }

        comparison = []
        for key, data in all_items.items():
            prices = {}
            for r, info in data['restaurants'].items():
                if info.get('price') is not None:
                    prices[r] = info['price']
            cheapest = min(prices, key=prices.get) if prices else None

            entry = {
                'item_name': data['item_name'],
                'category': data.get('category'),
                'is_veg': data.get('is_veg'),
                'cheapest_restaurant': cheapest,
                'restaurants': {},
            }
            for rname in restaurant_names:
                rdata = data['restaurants'].get(rname, {})
                entry['restaurants'][rname] = rdata.get('price')
            comparison.append(entry)

        return {
            'platform': platform,
            'platform_label': PLATFORM_LABELS.get(platform, platform),
            'restaurants': restaurant_names,
            'items': comparison,
        }

    def compare_delivery(self, restaurant_names=None):
        """Full delivery comparison across restaurants and platforms."""
        if restaurant_names is None:
            restaurant_names = self.get_restaurant_names()

        result = []
        for rname in restaurant_names:
            entry = {
                'restaurant_name': rname,
                'platforms': {},
            }
            for platform in PLATFORMS:
                fees = self.get_platform_delivery_fees(rname, platform)
                entry['platforms'][platform] = fees
            result.append(entry)
        return result

    def get_category_comparison(self, category, platform='instore', restaurant_names=None):
        """Get comparison filtered by category."""
        if restaurant_names is None:
            restaurant_names = self.get_restaurant_names()

        result = []
        target_cat = category.lower()
        for rname in restaurant_names:
            menu = self.get_platform_menu(rname, platform)
            category_items = []
            
            for item in menu:
                item_cat = (item.get('category') or '').lower()
                item_name = (item.get('item_name') or '').lower()

                # 0. Special trait-based and item-based categories
                if target_cat == 'veg':
                    if item.get('is_veg') is True:
                        category_items.append(item)
                    continue
                elif target_cat == 'non-veg':
                    if item.get('is_veg') is False:
                        category_items.append(item)
                    continue
                elif target_cat == 'rice':
                    if 'rice' in item_name or 'rice' in item_cat:
                        category_items.append(item)
                    continue
                elif target_cat == 'samosa':
                    if 'samosa' in item_name or 'samosa' in item_cat:
                        category_items.append(item)
                    continue
                
                # 1. Exact or plural match
                if item_cat == target_cat or item_cat.rstrip('s') == target_cat.rstrip('s') or item_cat.replace('ies', 'y') == target_cat.replace('ies', 'y'):
                    category_items.append(item)
                    continue
                    
                # 2. Substring match for base words
                if target_cat.rstrip('s') in item_cat or item_cat.rstrip('s') in target_cat:
                    category_items.append(item)
                    continue
                    
                # 3. Common synonym mapping
                if target_cat == 'curries' and 'curry' in item_cat:
                    category_items.append(item)
                elif target_cat == 'starters' and 'appetizer' in item_cat:
                    category_items.append(item)
                elif target_cat == 'desserts' and 'dessert' in item_cat:
                    category_items.append(item)
                elif target_cat == 'drinks' and 'beverage' in item_cat:
                    category_items.append(item)
                elif target_cat == 'bread' and 'naan' in item_cat:
                    category_items.append(item)
                elif target_cat == 'combos' and ('combo' in item_cat or 'special' in item_cat or 'pack' in item_cat):
                    category_items.append(item)
            result.append({
                'restaurant_name': rname,
                'items': category_items,
                'item_count': len(category_items),
            })
        return {
            'category': category,
            'platform': platform,
            'platform_label': PLATFORM_LABELS.get(platform, platform),
            'restaurants': result,
        }

    def get_platform_urls(self, restaurant_name):
        """Get external platform URLs (UberEats, DoorDash, Grubhub, Google Maps) for a restaurant.
        Returns dict with platform_name -> URL mappings.
        All URLs are anchored to the configured restaurant address (Leander TX) not the user's IP."""
        from urllib.parse import quote_plus
        from config import Config
        urls = {}
        delivery_platforms = ['ubereats', 'doordash', 'grubhub']
        for platform in delivery_platforms:
            adapter = _get_adapter(platform)
            if adapter and adapter.is_available() and hasattr(adapter, 'fetch_platform_url'):
                try:
                    url = adapter.fetch_platform_url(restaurant_name)
                    urls[f'{platform}_url'] = url
                except Exception as e:
                    print(f"[PlatformService] Error fetching {platform} URL for {restaurant_name}: {e}")
                    urls[f'{platform}_url'] = None
            else:
                urls[f'{platform}_url'] = None

        # Always include in-store / Google Maps link anchored to configured lat/lng
        lat = Config.CLIENT_LAT
        lng = Config.CLIENT_LNG
        address = Config.CLIENT_RESTAURANT_ADDRESS
        # Use coordinates for precise pin, with restaurant name as query
        maps_url = (
            f"https://www.google.com/maps/search/{quote_plus(restaurant_name)}"
            f"/@{lat},{lng},15z"
        )
        urls['instore_url'] = maps_url
        urls['google_maps_url'] = maps_url
        return urls

    def get_bulk_platform_urls(self, restaurant_names):
        """Get platform URLs for multiple restaurants at once.
        Returns dict: {restaurant_name: {ubereats_url, doordash_url, grubhub_url, instore_url}}"""
        result = {}
        for rname in restaurant_names:
            result[rname] = self.get_platform_urls(rname)
        return result

    def get_all_verification_links(self, restaurant_name, restaurant_address=None):
        """Get ALL platform verification links for a restaurant — always location-anchored.
        
        Returns links for in-store (Google Maps), UberEats, DoorDash, Grubhub.
        Fallback URLs include city/state to prevent wrong-location results.
        """
        from urllib.parse import quote_plus
        from config import Config

        if not restaurant_address:
            # For client restaurant, use configured address; for competitors use name
            restaurant_address = Config.CLIENT_RESTAURANT_ADDRESS

        # Parse location context
        parts = [p.strip() for p in restaurant_address.split(',') if p.strip()]
        city_state = f"{parts[-3]} {parts[-2].split()[0]}" if len(parts) >= 3 else ""
        zip_code = parts[-2].split()[-1] if len(parts) >= 2 and len(parts[-2].split()) >= 2 else ""

        # Build all platform links
        urls = self.get_platform_urls(restaurant_name)

        # Build Google Maps URL anchored to configured coordinates
        lat = Config.CLIENT_LAT
        lng = Config.CLIENT_LNG
        maps_url = (
            f"https://www.google.com/maps/search/{quote_plus(restaurant_name)}"
            f"/@{lat},{lng},15z"
        )

        return {
            'restaurant_name': restaurant_name,
            'restaurant_address': restaurant_address,
            'city_state': city_state,
            'location': {'lat': lat, 'lng': lng},
            'verification_links': {
                'instore': {
                    'label': 'In-Store / Google Maps',
                    'url': maps_url,
                    'description': f'View restaurant location near {city_state}',
                },
                'ubereats': {
                    'label': 'Uber Eats',
                    'url': urls.get('ubereats_url'),
                    'description': f'Check prices on Uber Eats near {city_state}',
                },
                'doordash': {
                    'label': 'DoorDash',
                    'url': urls.get('doordash_url'),
                    'description': f'Check prices on DoorDash near {city_state}',
                },
                'grubhub': {
                    'label': 'Grubhub',
                    'url': urls.get('grubhub_url'),
                    'description': f'Check prices on Grubhub near {city_state}',
                },
            },
        }

    # ── Private helpers ────────────────────────────────

    def _build_price_comparison(self, client_name, client_menu, comp_name, comp_menu, platform):
        """Build item-level price comparison between client and one competitor."""
        matches = matching_service.match_menus(client_menu, comp_menu)

        items = []
        for m in matches:
            item_a = m.get('item_a')
            item_b = m.get('item_b')

            if item_a and item_b:
                price_a = item_a.get('price')
                price_b = item_b.get('price')
                diff = round(price_a - price_b, 2) if price_a and price_b else None
                pct_diff = round((diff / price_b) * 100, 1) if diff is not None and price_b else None
                cheaper = None
                if diff is not None:
                    cheaper = client_name if diff <= 0 else comp_name

                items.append({
                    'item_name': item_a.get('item_name', ''),
                    'category': item_a.get('category'),
                    'client_price': price_a,
                    'competitor_price': price_b,
                    'price_difference': diff,
                    'percentage_difference': pct_diff,
                    'cheaper_restaurant': cheaper,
                    'match_score': m.get('score', 0),
                })
            elif item_a:
                items.append({
                    'item_name': item_a.get('item_name', ''),
                    'category': item_a.get('category'),
                    'client_price': item_a.get('price'),
                    'competitor_price': None,
                    'price_difference': None,
                    'percentage_difference': None,
                    'cheaper_restaurant': None,
                    'match_score': 0,
                })
            elif item_b:
                items.append({
                    'item_name': item_b.get('item_name', ''),
                    'category': item_b.get('category'),
                    'client_price': None,
                    'competitor_price': item_b.get('price'),
                    'price_difference': None,
                    'percentage_difference': None,
                    'cheaper_restaurant': None,
                    'match_score': 0,
                })

        client_prices = [i['client_price'] for i in items if i['client_price'] is not None]
        comp_prices = [i['competitor_price'] for i in items if i['competitor_price'] is not None]
        matched_items = [i for i in items if i['client_price'] is not None and i['competitor_price'] is not None]
        client_cheaper_count = sum(1 for i in matched_items if (i['price_difference'] or 0) <= 0)

        return {
            'client_name': client_name,
            'competitor_name': comp_name,
            'platform': platform,
            'platform_label': PLATFORM_LABELS.get(platform, platform),
            'items': items,
            'total_matched': len(matched_items),
            'client_cheaper_count': client_cheaper_count,
            'competitor_cheaper_count': len(matched_items) - client_cheaper_count,
            'client_avg_price': round(sum(client_prices) / len(client_prices), 2) if client_prices else None,
            'competitor_avg_price': round(sum(comp_prices) / len(comp_prices), 2) if comp_prices else None,
        }

    def _build_platform_comparison(self, client_name, client_menu, client_instore,
                                    comp_name, comp_menu, comp_instore, platform):
        """Build platform comparison with markup over in-store."""
        base = self._build_price_comparison(client_name, client_menu, comp_name, comp_menu, platform)

        # Add markup info
        client_instore_lookup = {
            matching_service.normalize_name(i.get('item_name', '')): i.get('price')
            for i in client_instore if i.get('price')
        }
        comp_instore_lookup = {
            matching_service.normalize_name(i.get('item_name', '')): i.get('price')
            for i in comp_instore if i.get('price')
        }

        for item in base['items']:
            name = item.get('item_name', '')
            norm = matching_service.normalize_name(name)

            # Client markup
            client_base = client_instore_lookup.get(norm)
            if client_base and item.get('client_price'):
                item['client_markup'] = round(item['client_price'] - client_base, 2)
                item['client_markup_pct'] = round(((item['client_price'] - client_base) / client_base) * 100, 1)
            else:
                item['client_markup'] = None
                item['client_markup_pct'] = None

            # Competitor markup
            comp_base = comp_instore_lookup.get(norm)
            if comp_base and item.get('competitor_price'):
                item['competitor_markup'] = round(item['competitor_price'] - comp_base, 2)
                item['competitor_markup_pct'] = round(((item['competitor_price'] - comp_base) / comp_base) * 100, 1)
            else:
                item['competitor_markup'] = None
                item['competitor_markup_pct'] = None

        # Add delivery fee comparison
        client_fees = self.get_platform_delivery_fees(client_name, platform)
        comp_fees = self.get_platform_delivery_fees(comp_name, platform)
        base['client_delivery'] = client_fees
        base['competitor_delivery'] = comp_fees

        return base

    def _empty_fees(self):
        return {
            'delivery_fee': None,
            'service_fee': None,
            'surge_fee': None,
            'tax_estimate': None,
            'free_delivery_threshold': None,
            'min_order_amount': None,
            'estimated_delivery_time': None,
        }


# Singleton
platform_service = PlatformService()
