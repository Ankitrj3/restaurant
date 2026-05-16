"""Comparison and analysis routes."""

from flask import Blueprint, jsonify, request
from services.competitor_service import competitor_service
from services.comparison_service import comparison_service

comparison_bp = Blueprint('comparison', __name__)


@comparison_bp.route('/api/comparison/<int:restaurant_idx>', methods=['GET'])
def compare_restaurant(restaurant_idx):
    """One-to-one comparison between client and a competitor."""
    data = competitor_service.find_competitors()
    restaurants = data['restaurants']

    if restaurant_idx < 0 or restaurant_idx >= len(restaurants):
        return jsonify({"error": "Invalid restaurant index"}), 404

    competitor = restaurants[restaurant_idx]
    competitor['menu'] = competitor_service.get_restaurant_menu(competitor)
    competitor['offers'] = competitor_service.get_restaurant_offers(competitor)

    client_data = {
        **competitor_service.client_restaurant,
        'menu': competitor_service.get_client_menu(),
        'offers': competitor_service.get_client_offers(),
    }

    result = comparison_service.compare(client_data, competitor)
    result['client_restaurant'] = competitor_service.client_restaurant
    result['competitor_restaurant'] = {
        'name': competitor['name'],
        'address': competitor.get('address', ''),
        'rating': competitor.get('rating', 0),
        'distance_miles': competitor.get('distance_miles', 0),
        'price_category': competitor.get('price_category', '$$'),
    }
    return jsonify(result)


@comparison_bp.route('/api/analysis/market', methods=['GET'])
def market_analysis():
    """Generate market-wide analysis."""
    data = competitor_service.find_competitors()
    client_data = {
        **competitor_service.client_restaurant,
        'menu': competitor_service.get_client_menu(),
        'offers': competitor_service.get_client_offers(),
    }
    competitors = []
    for r in data['restaurants']:
        r['menu'] = competitor_service.get_restaurant_menu(r)
        r['offers'] = competitor_service.get_restaurant_offers(r)
        competitors.append(r)

    result = comparison_service.generate_market_analysis(client_data, competitors)
    return jsonify(result)


@comparison_bp.route('/api/analysis/pricing', methods=['GET'])
def pricing_analysis():
    """Generate pricing optimization analysis."""
    data = competitor_service.find_competitors()
    client_menu = competitor_service.get_client_menu()
    comp_menus = [competitor_service.get_restaurant_menu(r) for r in data['restaurants']]

    result = comparison_service.generate_pricing_analysis(client_menu, comp_menus)
    return jsonify(result)


@comparison_bp.route('/api/analysis/recommendations', methods=['GET'])
def recommendations():
    """Get AI-powered recommendations for the client restaurant."""
    data = competitor_service.find_competitors()
    client_data = {
        **competitor_service.client_restaurant,
        'menu': competitor_service.get_client_menu(),
        'offers': competitor_service.get_client_offers(),
    }
    comp_data = []
    for r in data['restaurants'][:5]:
        r['menu'] = competitor_service.get_restaurant_menu(r)
        r['offers'] = competitor_service.get_restaurant_offers(r)
        comp_data.append(r)

    result = comparison_service.generate_market_analysis(client_data, comp_data)
    return jsonify(result)
