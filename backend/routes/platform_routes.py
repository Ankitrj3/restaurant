"""
Platform comparison and analytics routes.
Provides REST endpoints for multi-platform menu comparison,
delivery fee comparison, category analytics, and admin config.
"""

import json
from flask import Blueprint, jsonify, request
from services.platform_service import platform_service, PLATFORMS, PLATFORM_LABELS, STANDARD_CATEGORIES
from config import Config

platform_bp = Blueprint('platform', __name__)


# ── Market Intelligence Matrix ─────────────────────────

@platform_bp.route('/api/market-matrix', methods=['GET'])
def get_market_matrix():
    """Generate the full competitive pricing matrix.
    
    Uses Gemini with Google Search grounding to fetch REAL data from:
    - Restaurant official websites (in-store prices)
    - UberEats listings
    - DoorDash listings  
    - Grubhub listings
    
    Query params:
        radius (float): Scan boundary in miles (default: 10.0)
        format (str): 'json' (minified, default) or 'pretty' (indented)
    
    Returns the enforced JSON schema with matrix[], logistics_comparison[],
    cross-platform price variance, and delivery threshold flags.
    """
    try:
        radius = request.args.get('radius', 10.0, type=float)
        fmt = request.args.get('format', 'json')
        
        from services.market_matrix_service import market_matrix_service
        result = market_matrix_service.generate_matrix(radius_miles=radius)
        
        if fmt == 'pretty':
            return app_jsonify_pretty(result)
        
        # Minified JSON (default)
        return jsonify(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'market_center': Config.CLIENT_RESTAURANT_NAME,
            'matrix': [],
            'logistics_comparison': []
        }), 500


def app_jsonify_pretty(data):
    """Return pretty-printed JSON response."""
    import json as json_module
    return json_module.dumps(data, indent=2, default=str), 200, {
        'Content-Type': 'application/json'
    }



@platform_bp.route('/api/restaurants/list', methods=['GET'])
def list_restaurants():
    """List all known restaurant names."""
    try:
        names = platform_service.get_restaurant_names()
        return jsonify({'restaurants': names})
    except Exception as e:
        return jsonify({'restaurants': [Config.CLIENT_RESTAURANT_NAME], 'error': str(e)})


@platform_bp.route('/api/categories', methods=['GET'])
def list_categories():
    """List all supported categories."""
    try:
        restaurant = request.args.get('restaurant')
        cats = platform_service.get_all_categories(restaurant)
        return jsonify({'categories': cats, 'standard': STANDARD_CATEGORIES})
    except Exception as e:
        return jsonify({'categories': STANDARD_CATEGORIES, 'error': str(e)})


@platform_bp.route('/api/platforms', methods=['GET'])
def list_platforms():
    """List all supported platforms."""
    return jsonify({
        'platforms': PLATFORMS,
        'labels': PLATFORM_LABELS,
    })


# ── Platform URL Endpoints ─────────────────────────────

@platform_bp.route('/api/platforms/urls', methods=['GET'])
def get_platform_urls():
    """Get real external platform URLs (UberEats, DoorDash, Grubhub) for a restaurant.
    
    Query params:
        restaurant (str): Restaurant name (default: client restaurant)
    
    Returns:
        { restaurant, ubereats_url, doordash_url, grubhub_url }
    """
    restaurant = request.args.get('restaurant', Config.CLIENT_RESTAURANT_NAME)
    try:
        urls = platform_service.get_platform_urls(restaurant)
        return jsonify({
            'restaurant': restaurant,
            **urls,
        })
    except Exception as e:
        return jsonify({'restaurant': restaurant, 'error': str(e)}), 500


@platform_bp.route('/api/platforms/urls/bulk', methods=['GET'])
def get_bulk_platform_urls():
    """Get platform URLs for multiple restaurants at once.
    
    Query params:
        restaurants (str): Comma-separated restaurant names
    
    Returns:
        { urls: { restaurant_name: { ubereats_url, doordash_url, grubhub_url, instore_url } } }
    """
    restaurants_param = request.args.get('restaurants', '')
    if restaurants_param:
        restaurant_names = [r.strip() for r in restaurants_param.split(',') if r.strip()]
    else:
        restaurant_names = platform_service.get_restaurant_names()

    try:
        urls = platform_service.get_bulk_platform_urls(restaurant_names)
        return jsonify({'urls': urls})
    except Exception as e:
        return jsonify({'urls': {}, 'error': str(e)}), 500


@platform_bp.route('/api/platforms/verification-links', methods=['GET'])
def get_verification_links():
    """Get ALL platform verification links for a restaurant — always location-anchored.

    Returns links for in-store (Google Maps), UberEats, DoorDash, Grubhub.
    All links are anchored to the configured restaurant's city/state from .env,
    so they always show the correct US location regardless of the user's IP or physical location.

    Query params:
        restaurant (str): Restaurant name (default: client restaurant from .env)
        address (str): Optional restaurant address override

    Returns:
        {
            restaurant_name, restaurant_address, city_state,
            location: { lat, lng },
            verification_links: {
                instore: { label, url, description },
                ubereats: { label, url, description },
                doordash: { label, url, description },
                grubhub:  { label, url, description }
            }
        }
    """
    restaurant = request.args.get('restaurant', Config.CLIENT_RESTAURANT_NAME)
    address = request.args.get('address')
    try:
        result = platform_service.get_all_verification_links(restaurant, address)
        return jsonify(result)
    except Exception as e:
        return jsonify({'restaurant_name': restaurant, 'error': str(e)}), 500


# ── Platform Menu Endpoints ────────────────────────────

@platform_bp.route('/api/platforms/menu', methods=['GET'])
def get_platform_menu():
    """Get menu for a restaurant on a specific platform.
    
    Response includes 'data_source_info' showing which websites were searched
    and whether data came from live Gemini grounding or a fallback.
    """
    restaurant = request.args.get('restaurant', Config.CLIENT_RESTAURANT_NAME)
    platform = request.args.get('platform', 'instore')
    try:
        menu = platform_service.get_platform_menu(restaurant, platform)

        # Determine data source type and grounding URLs
        source_types = list({item.get('source', 'unknown') for item in menu if isinstance(item, dict)})
        is_live = any('grounded' in s for s in source_types)
        is_fallback = any('fallback' in s for s in source_types)

        # Collect any grounding URLs from the registry for this platform
        from services.gemini_service import get_source_registry
        registry = get_source_registry()
        domain_map = {
            'ubereats': 'ubereats.com',
            'doordash': 'doordash.com',
            'grubhub': 'grubhub.com',
            'instore': None,
        }
        domain = domain_map.get(platform)
        grounding_urls = []
        seen = set()
        for label, sources in registry.items():
            for s in sources:
                url = s.get('url', '')
                if url not in seen and (not domain or domain in url):
                    grounding_urls.append({'url': url, 'title': s.get('title', ''), 'call': label})
                    seen.add(url)

        data_source_info = {
            'data_source': source_types[0] if len(source_types) == 1 else source_types,
            'is_live_grounded_data': is_live,
            'is_fallback_data': is_fallback,
            'grounding_urls': grounding_urls,
            'grounding_url_count': len(grounding_urls),
            'note': (
                'Data fetched live from the web via Gemini Google Search grounding.'
                if is_live else
                'Data is AI-estimated (Gemini fallback). Live grounding URLs not available — '
                'check Gemini API key/rate limits.'
            ),
        }

        return jsonify({
            'restaurant': restaurant,
            'platform': platform,
            'platform_label': PLATFORM_LABELS.get(platform, platform),
            'items': menu,
            'total_items': len(menu),
            'data_source_info': data_source_info,
        })
    except Exception as e:
        return jsonify({'restaurant': restaurant, 'platform': platform, 'items': [], 'error': str(e)})


# ── Shared helper: attach source URL info to any comparison result ─────────────

def _attach_source_urls(result, platform, client_name='', competitor_name=''):
    """Inject data_source_info into a comparison result dict.

    Looks up the Gemini grounding registry for URLs matching the platform domain
    and the restaurant names, so the frontend can show clickable source links.
    """
    try:
        from services.gemini_service import get_source_registry
        registry = get_source_registry()

        domain_map = {
            'ubereats': 'ubereats.com',
            'doordash': 'doordash.com',
            'grubhub': 'grubhub.com',
            'instore': None,
        }
        domain = domain_map.get(platform)

        def _urls_for(name):
            """Return grounding URLs that relate to this restaurant name."""
            name_lower = name.lower()
            urls = []
            seen: set = set()
            for label, sources in registry.items():
                label_match = name_lower in label.lower()
                for s in sources:
                    url = s.get('url', '')
                    if not url or url in seen:
                        continue
                    domain_match = (not domain) or (domain in url)
                    if label_match or domain_match:
                        urls.append({'url': url, 'title': s.get('title', '')})
                        seen.add(url)
            return urls

        # Detect live data: check if the Gemini registry has ANY entries
        # (meaning grounded API calls were made successfully), or if comparison
        # items carry a 'source' field with 'grounded'/'live' in it.
        registry_has_entries = len(registry) > 0

        # Also check items for source field (may be present in raw menu results)
        items = result.get('items', []) if isinstance(result, dict) else []
        source_types = list({str(item.get('source', ''))
                             for item in items if isinstance(item, dict) and item.get('source')})

        has_grounded_source = any('grounded' in s or 'live' in s for s in source_types)

        # The data is live if EITHER the registry has entries OR items have grounded source tags
        is_live = registry_has_entries or has_grounded_source
        is_fallback = not is_live

        client_urls = _urls_for(client_name)
        competitor_urls = _urls_for(competitor_name)
        all_platform = [
            {'url': s.get('url', ''), 'title': s.get('title', '')}
            for sources in registry.values()
            for s in sources
            if domain and domain in s.get('url', '')
        ]

        # Build search queries list from registry
        search_queries = []
        for label, sources in registry.items():
            for s in sources:
                for q in s.get('search_queries', []):
                    if q and q not in search_queries:
                        search_queries.append(q)

        data_source = 'google_search_grounding' if is_live else 'fallback_estimated'

        result['data_source_info'] = {
            'platform': platform,
            'platform_label': PLATFORM_LABELS.get(platform, platform),
            'is_live_grounded_data': is_live,
            'is_fallback_data': is_fallback,
            'data_source': data_source,
            'search_queries': search_queries[:10],
            'client_sources': {
                'name': client_name,
                'grounding_urls': client_urls,
            },
            'competitor_sources': {
                'name': competitor_name,
                'grounding_urls': competitor_urls,
            },
            'all_platform_urls': all_platform,
            'registry_url': f'/api/data-sources/platform/{platform}',
            'note': (
                f'Prices fetched live from {PLATFORM_LABELS.get(platform, platform)} via Gemini Google Search grounding.'
                if is_live else
                f'Prices are AI-estimated. Gemini could not find this restaurant on '
                f'{PLATFORM_LABELS.get(platform, platform)} — check Gemini API key/rate limits.'
            ),
        }
    except Exception as e:
        result['data_source_info'] = {'error': str(e), 'registry_url': '/api/data-sources'}
    return result


def _attach_platform_urls(result, platform, client_name='', competitor_name=''):
    """Inject platform URLs into the comparison result's data_source_info."""
    if 'data_source_info' not in result:
        result['data_source_info'] = {}
    
    url_key = f"{platform}_url"
    
    # Get client URL
    client_url = None
    if client_name:
        try:
            urls = platform_service.get_platform_urls(client_name)
            client_url = urls.get(url_key)
        except Exception:
            pass
            
    # Get competitor URL
    competitor_url = None
    if competitor_name:
        try:
            urls = platform_service.get_platform_urls(competitor_name)
            competitor_url = urls.get(url_key)
        except Exception:
            pass
            
    result['data_source_info']['client_platform_url'] = client_url
    result['data_source_info']['competitor_platform_url'] = competitor_url
    return result


# ── In-Store Comparison ────────────────────────────────

@platform_bp.route('/api/comparison/instore', methods=['GET'])
def compare_instore():
    """Compare Bawarchi in-store prices vs competitors."""
    competitor = request.args.get('competitor')
    try:
        from services.competitor_service import competitor_service
        client_name = competitor_service.client_restaurant.get('name', '')
        result = platform_service.compare_instore(competitor)
        # Attach source URLs to each comparison object
        if isinstance(result, list):
            for r in result:
                comp_name = r.get('competitor_name', competitor or '')
                _attach_source_urls(r, 'instore', client_name, comp_name)
        elif isinstance(result, dict):
            comp_name = result.get('competitor_name', competitor or '')
            _attach_source_urls(result, 'instore', client_name, comp_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'items': []}), 500


# ── Platform-Specific Comparison ───────────────────────

@platform_bp.route('/api/comparison/platform/<platform>', methods=['GET'])
def compare_platform(platform):
    """Compare pricing on a specific platform (ubereats/doordash/grubhub)."""
    if platform not in PLATFORMS:
        return jsonify({'error': f'Unsupported platform: {platform}'}), 400
    competitor = request.args.get('competitor')
    try:
        from services.competitor_service import competitor_service
        client_name = competitor_service.client_restaurant.get('name', '')
        result = platform_service.compare_platform(platform, competitor)
        # Attach source URLs and platform URLs to each comparison object
        if isinstance(result, list):
            for r in result:
                comp_name = r.get('competitor_name', competitor or '')
                _attach_source_urls(r, platform, client_name, comp_name)
                _attach_platform_urls(r, platform, client_name, comp_name)
        elif isinstance(result, dict):
            comp_name = result.get('competitor_name', competitor or '')
            _attach_source_urls(result, platform, client_name, comp_name)
            _attach_platform_urls(result, platform, client_name, comp_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'items': []}), 500


# ── Platform vs Platform ───────────────────────────────

@platform_bp.route('/api/comparison/platform-vs-platform', methods=['GET'])
def compare_platform_to_platform():
    """Compare prices across platforms for one restaurant."""
    restaurant = request.args.get('restaurant')
    try:
        result = platform_service.compare_platform_to_platform(restaurant)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'items': []}), 500


# ── Restaurant vs Restaurant ──────────────────────────

@platform_bp.route('/api/comparison/restaurant-vs-restaurant', methods=['GET'])
def compare_restaurant_to_restaurant():
    """Compare multiple restaurants on the same platform."""
    platform = request.args.get('platform', 'instore')
    restaurants_param = request.args.get('restaurants', '')

    if restaurants_param:
        restaurant_names = [r.strip() for r in restaurants_param.split(',') if r.strip()]
    else:
        restaurant_names = platform_service.get_restaurant_names()

    try:
        result = platform_service.compare_restaurant_to_restaurant(restaurant_names, platform)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'items': []}), 500


# ── Delivery Comparison ───────────────────────────────

@platform_bp.route('/api/comparison/delivery', methods=['GET'])
def compare_delivery():
    """Full delivery fee comparison across restaurants and platforms."""
    try:
        result = platform_service.compare_delivery()
        return jsonify({'comparisons': result, 'platforms': PLATFORMS})
    except Exception as e:
        return jsonify({'comparisons': [], 'error': str(e)})


@platform_bp.route('/api/platforms/delivery-fees', methods=['GET'])
def get_delivery_fees():
    """Get delivery fees for all restaurants."""
    try:
        result = platform_service.get_all_delivery_fees()
        return jsonify({'fees': result, 'platforms': PLATFORMS})
    except Exception as e:
        return jsonify({'fees': [], 'error': str(e)})


@platform_bp.route('/api/platforms/free-delivery', methods=['GET'])
def get_free_delivery():
    """Get free delivery thresholds for all restaurants."""
    try:
        result = platform_service.get_free_delivery_thresholds()
        return jsonify({'thresholds': result, 'platforms': PLATFORMS})
    except Exception as e:
        return jsonify({'thresholds': [], 'error': str(e)})


# ── Category Analytics ─────────────────────────────────

@platform_bp.route('/api/comparison/category/<category>', methods=['GET'])
def compare_category(category):
    """Get comparison filtered by category."""
    platform = request.args.get('platform', 'instore')
    try:
        result = platform_service.get_category_comparison(category, platform)
        return jsonify(result)
    except Exception as e:
        return jsonify({'category': category, 'restaurants': [], 'error': str(e)})


# ── Admin Config ───────────────────────────────────────

@platform_bp.route('/api/config', methods=['GET'])
def get_config():
    """Get current platform configuration."""
    return jsonify({
        'platforms': {
            'ubereats': {'enabled': Config.UBEREATS_SCRAPE_ENABLED, 'label': 'Uber Eats'},
            'doordash': {'enabled': Config.DOORDASH_SCRAPE_ENABLED, 'label': 'DoorDash'},
            'grubhub': {'enabled': Config.GRUBHUB_SCRAPE_ENABLED, 'label': 'Grubhub'},
        },
        'cache_ttl': Config.PLATFORM_CACHE_TTL,
        'scraping_fallback': Config.SCRAPING_FALLBACK_ENABLED,
        'fuzzy_threshold': Config.FUZZY_MATCH_THRESHOLD,
        'client_restaurant': Config.CLIENT_RESTAURANT_NAME,
        'client_address': Config.CLIENT_RESTAURANT_ADDRESS,
    })


@platform_bp.route('/api/config', methods=['POST'])
def update_config():
    """Update platform configuration (runtime only, not persisted to .env)."""
    data = request.get_json(silent=True) or {}

    if 'ubereats_enabled' in data:
        Config.UBEREATS_SCRAPE_ENABLED = bool(data['ubereats_enabled'])
    if 'doordash_enabled' in data:
        Config.DOORDASH_SCRAPE_ENABLED = bool(data['doordash_enabled'])
    if 'grubhub_enabled' in data:
        Config.GRUBHUB_SCRAPE_ENABLED = bool(data['grubhub_enabled'])
    if 'cache_ttl' in data:
        Config.PLATFORM_CACHE_TTL = int(data['cache_ttl'])
    if 'scraping_fallback' in data:
        Config.SCRAPING_FALLBACK_ENABLED = bool(data['scraping_fallback'])
    if 'fuzzy_threshold' in data:
        Config.FUZZY_MATCH_THRESHOLD = float(data['fuzzy_threshold'])

    return jsonify({'status': 'ok', 'message': 'Configuration updated'})


# ── Data Sources (Grounding URLs) ────────────────────────────────

@platform_bp.route('/api/data-sources', methods=['GET'])
def get_data_sources():
    """Return all real web URLs that Gemini searched to populate menu/price data.
    
    This reveals exactly which website pages (UberEats, DoorDash, restaurant sites, etc.)
    Gemini used as ground truth for pricing data.

    Query params:
        platform (str): Filter by platform keyword (ubereats, doordash, grubhub, instore)
        flat (bool): If 'true', return a flat list instead of grouped by call
    """
    try:
        from services.gemini_service import get_source_registry
        registry = get_source_registry()

        platform_filter = request.args.get('platform', '').lower()
        flat_mode = request.args.get('flat', 'false').lower() == 'true'

        # Also pull _sources from cached menu results
        from services.cache_service import cache_service
        cache_sources = _collect_sources_from_cache(platform_filter)

        # Merge cache sources into registry
        for label, sources in cache_sources.items():
            if label not in registry:
                registry[label] = []
            for s in sources:
                if s not in registry[label]:
                    registry[label].append(s)

        if platform_filter:
            filtered = {}
            for label, sources in registry.items():
                if platform_filter in label.lower():
                    filtered[label] = sources
            # Also include sources whose URLs match the platform domain
            domain_map = {
                'ubereats': 'ubereats.com',
                'doordash': 'doordash.com',
                'grubhub': 'grubhub.com',
                'instore': None,
            }
            domain = domain_map.get(platform_filter)
            if domain:
                for label, sources in registry.items():
                    matching = [s for s in sources if domain in s.get('url', '')]
                    if matching:
                        key = f"{label} [{platform_filter}]"
                        filtered.setdefault(key, []).extend(matching)
            registry = filtered

        if flat_mode:
            flat = []
            seen_urls = set()
            for sources in registry.values():
                for s in sources:
                    if s.get('url') not in seen_urls:
                        flat.append(s)
                        seen_urls.add(s.get('url'))
            return jsonify({
                'total_sources': len(flat),
                'platform_filter': platform_filter or 'all',
                'sources': flat,
            })

        # Default: grouped
        total = sum(len(v) for v in registry.values())
        return jsonify({
            'total_sources': total,
            'platform_filter': platform_filter or 'all',
            'grouped_sources': registry,
        })

    except Exception as e:
        return jsonify({'error': str(e), 'sources': []}), 500


@platform_bp.route('/api/data-sources/platform/<platform>', methods=['GET'])
def get_platform_data_sources(platform):
    """Return all real web URLs used specifically for a given platform.
    
    Platform values: ubereats, doordash, grubhub, instore
    """
    domain_map = {
        'ubereats': 'ubereats.com',
        'doordash': 'doordash.com',
        'grubhub': 'grubhub.com',
        'instore': None,
    }
    if platform not in domain_map:
        return jsonify({'error': f'Unknown platform: {platform}. Use: ubereats, doordash, grubhub, instore'}), 400

    try:
        from services.gemini_service import get_source_registry
        registry = get_source_registry()
        domain = domain_map.get(platform)

        # Collect all sources that mention this platform's domain
        matched = []
        seen_urls = set()
        for label, sources in registry.items():
            for s in sources:
                url = s.get('url', '')
                if url in seen_urls:
                    continue
                if domain and domain in url:
                    matched.append({**s, '_call_label': label})
                    seen_urls.add(url)
                elif not domain and platform in label.lower():
                    matched.append({**s, '_call_label': label})
                    seen_urls.add(url)

        # Also pull from cached menu data
        cache_sources = _collect_sources_from_cache(platform)
        for label, sources in cache_sources.items():
            for s in sources:
                url = s.get('url', '')
                if url not in seen_urls:
                    matched.append({**s, '_call_label': label})
                    seen_urls.add(url)

        return jsonify({
            'platform': platform,
            'platform_label': PLATFORM_LABELS.get(platform, platform),
            'domain': domain,
            'total_sources': len(matched),
            'sources': matched,
            'note': 'These are the real web pages Gemini searched to get menu/price data for this platform.',
        })
    except Exception as e:
        return jsonify({'error': str(e), 'sources': []}), 500


def _collect_sources_from_cache(platform_filter=''):
    """Scan the memory cache for any saved _sources fields from grounded calls.
    
    The cache service stores entries in _memory_cache as a flat dict with keys
    formatted as 'category:key' (e.g., 'menu:ubereats_bawarchi').
    """
    result = {}
    try:
        from services.cache_service import cache_service
        # _memory_cache is a flat dict: { "category:key": {"data": ..., "timestamp": ...} }
        for cache_key, entry in cache_service._memory_cache.items():
            data = entry.get('data') if isinstance(entry, dict) else None
            if not data:
                continue
            sources = None
            if isinstance(data, dict):
                sources = data.get('_sources')
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('_sources'):
                        sources = item['_sources']
                        break
            if sources:
                label = f"cache:{cache_key}"
                if not platform_filter or platform_filter in cache_key:
                    result[label] = sources
    except Exception:
        pass
    return result


# ── Export ─────────────────────────────────────────────

@platform_bp.route('/api/export/<report_type>', methods=['GET'])
def export_report(report_type):
    """Generate downloadable HTML report."""
    try:
        if report_type == 'instore':
            data = platform_service.compare_instore()
            title = 'In-Store Price Comparison Report'
        elif report_type == 'delivery':
            data = platform_service.compare_delivery()
            title = 'Delivery Fee Comparison Report'
        elif report_type == 'platform-vs-platform':
            restaurant = request.args.get('restaurant')
            data = platform_service.compare_platform_to_platform(restaurant)
            title = 'Platform vs Platform Comparison Report'
        elif report_type in ('ubereats', 'doordash', 'grubhub'):
            data = platform_service.compare_platform(report_type)
            title = f'{PLATFORM_LABELS.get(report_type, report_type)} Comparison Report'
        elif report_type == 'free-delivery':
            data = platform_service.get_free_delivery_thresholds()
            title = 'Free Delivery Threshold Report'
        else:
            return jsonify({'error': f'Unknown report type: {report_type}'}), 400

        html = _generate_html_report(title, data)
        return html, 200, {
            'Content-Type': 'text/html',
            'Content-Disposition': f'attachment; filename="{report_type}_report.html"',
        }
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _generate_html_report(title, data):
    """Generate a styled HTML report from comparison data."""
    data_json = json.dumps(data, default=str, indent=2)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title} — Bawarchi Analytics</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f8f6f2; color: #1f1b16; }}
h1 {{ color: #f26922; border-bottom: 3px solid #f26922; padding-bottom: 10px; }}
h2 {{ color: #4b4540; margin-top: 30px; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }}
th {{ background: #f26922; color: white; padding: 10px 14px; text-align: left; }}
td {{ padding: 8px 14px; border-bottom: 1px solid #ddd; }}
tr:hover td {{ background: #fff6ee; }}
.meta {{ color: #7c746c; font-size: 13px; margin-bottom: 20px; }}
.cheaper {{ color: #1f9d64; font-weight: 600; }}
.expensive {{ color: #e05252; }}
.na {{ color: #999; }}
pre {{ background: #fff; border: 1px solid #ddd; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 12px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="meta">Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Bawarchi Indian Cuisine & Bar</div>
<h2>Raw Data</h2>
<pre>{data_json}</pre>
<script>
// Parse and render tables from data
try {{
  const data = {data_json};
  const container = document.querySelector('body');
  const items = Array.isArray(data) ? data.flatMap(d => d.items || []) : (data.items || []);
  if (items.length) {{
    const keys = Object.keys(items[0]);
    let html = '<h2>Comparison Table</h2><table><thead><tr>';
    keys.forEach(k => html += '<th>' + k.replace(/_/g, ' ') + '</th>');
    html += '</tr></thead><tbody>';
    items.forEach(row => {{
      html += '<tr>';
      keys.forEach(k => {{
        let val = row[k];
        let cls = '';
        if (val === null || val === undefined) {{ val = 'N/A'; cls = 'na'; }}
        else if (typeof val === 'number') {{ val = val.toFixed(2); }}
        html += '<td class="' + cls + '">' + val + '</td>';
      }});
      html += '</tr>';
    }});
    html += '</tbody></table>';
    container.insertAdjacentHTML('afterbegin', html);
  }}
}} catch(e) {{}}
</script>
</body>
</html>"""
