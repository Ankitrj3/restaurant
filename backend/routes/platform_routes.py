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


# ── Restaurant & Category Listings ─────────────────────

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


# ── Platform Menu Endpoints ────────────────────────────

@platform_bp.route('/api/platforms/menu', methods=['GET'])
def get_platform_menu():
    """Get menu for a restaurant on a specific platform."""
    restaurant = request.args.get('restaurant', Config.CLIENT_RESTAURANT_NAME)
    platform = request.args.get('platform', 'instore')
    try:
        menu = platform_service.get_platform_menu(restaurant, platform)
        return jsonify({
            'restaurant': restaurant,
            'platform': platform,
            'platform_label': PLATFORM_LABELS.get(platform, platform),
            'items': menu,
            'total_items': len(menu),
        })
    except Exception as e:
        return jsonify({'restaurant': restaurant, 'platform': platform, 'items': [], 'error': str(e)})


# ── In-Store Comparison ────────────────────────────────

@platform_bp.route('/api/comparison/instore', methods=['GET'])
def compare_instore():
    """Compare Bawarchi in-store prices vs competitors."""
    competitor = request.args.get('competitor')
    try:
        result = platform_service.compare_instore(competitor)
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
        result = platform_service.compare_platform(platform, competitor)
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
