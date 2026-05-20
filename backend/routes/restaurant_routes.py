"""Restaurant search and listing routes."""

from flask import Blueprint, jsonify, request
from services.competitor_service import competitor_service

restaurant_bp = Blueprint('restaurants', __name__)


@restaurant_bp.route('/api/restaurants/search', methods=['GET'])
def search_restaurants():
    """Search nearby Indian restaurants with dynamic radius expansion."""
    max_radius = request.args.get('radius', 20, type=int)
    result = competitor_service.find_competitors(max_radius)
    # We skip full menu/offers scraping here to keep the listing fast.
    # The new multi-platform dashboard loads these asynchronously via PlatformService.
    for r in result['restaurants']:
        r['comparison_button'] = True
    return jsonify(result)


@restaurant_bp.route('/api/restaurants/<restaurant_id>', methods=['GET'])
def get_restaurant(restaurant_id):
    """Get details for a specific restaurant by index."""
    try:
        idx = int(restaurant_id)
        data = competitor_service.find_competitors()
        if 0 <= idx < len(data['restaurants']):
            r = data['restaurants'][idx]
            r['menu'] = competitor_service.get_restaurant_menu(r)
            r['offers'] = competitor_service.get_restaurant_offers(r)
            return jsonify(r)
    except (ValueError, IndexError):
        pass
    return jsonify({"error": "Restaurant not found"}), 404


@restaurant_bp.route('/api/client/menu', methods=['GET'])
def get_client_menu():
    """Get the client restaurant's menu."""
    return jsonify({
        "restaurant": competitor_service.client_restaurant,
        "menu": competitor_service.get_client_menu(),
        "offers": competitor_service.get_client_offers(),
    })
