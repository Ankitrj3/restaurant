"""Comparison and analysis routes."""

from __future__ import annotations

from typing import Any, cast

from flask import Blueprint, jsonify, request
from services.competitor_service import competitor_service
from services.comparison_service import comparison_service

comparison_bp = Blueprint('comparison', __name__)


# ── Helper ─────────────────────────────────────────────────────────────────────

def _build_source_info(
    restaurant_data: dict[str, Any],
    menu: list[dict[str, Any]],
    registry: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Return a dict describing where this restaurant's menu data came from."""
    source_types: list[str] = list({
        str(item.get('source', 'unknown'))
        for item in menu
        if isinstance(item, dict)
    })

    raw_website: Any = (
        restaurant_data.get('website_url') or restaurant_data.get('address', '')
    )
    website: str | None = (
        raw_website
        if isinstance(raw_website, str) and raw_website.startswith('http')
        else None
    )

    # Collect Gemini grounding URLs that mention this restaurant by name
    rname_lower: str = str(restaurant_data.get('name', '')).lower()
    grounding_urls: list[dict[str, str]] = []
    seen: set[str] = set()
    for label, sources in registry.items():
        if rname_lower in label.lower():
            for s in sources:
                url = str(s.get('url', ''))
                if url and url not in seen:
                    grounding_urls.append({
                        'url': url,
                        'title': str(s.get('title', '')),
                    })
                    seen.add(url)

    live_sources = {
        'client_live', 'competitor_live',
        'ubereats_grounded', 'doordash_grounded', 'grubhub_grounded',
    }
    is_live: bool = any(s in live_sources for s in source_types)

    return {
        'name': restaurant_data.get('name'),
        'source_types': source_types,
        'is_live_data': is_live,
        'website_url': website,
        'grounding_urls': grounding_urls,
        'note': (
            'Live data scraped from the restaurant website and/or delivery platforms.'
            if is_live else
            'Data is from demo/cache fallback — not live-scraped.'
        ),
    }


# ── Routes ─────────────────────────────────────────────────────────────────────

@comparison_bp.route('/api/comparison/<int:restaurant_idx>', methods=['GET'])
def compare_restaurant(restaurant_idx: int):
    """One-to-one comparison between the client and a specific competitor."""
    data = competitor_service.find_competitors()
    restaurants: list[dict[str, Any]] = cast(list[dict[str, Any]], data.get('restaurants', []))

    if restaurant_idx < 0 or restaurant_idx >= len(restaurants):
        return jsonify({'error': 'Invalid restaurant index'}), 404

    competitor: dict[str, Any] = restaurants[restaurant_idx]
    competitor['menu'] = competitor_service.get_restaurant_menu(competitor)
    competitor['offers'] = competitor_service.get_restaurant_offers(competitor)

    client_data: dict[str, Any] = {
        **competitor_service.client_restaurant,
        'menu': competitor_service.get_client_menu(),
        'offers': competitor_service.get_client_offers(),
    }

    result: dict[str, Any] | None = comparison_service.compare(client_data, competitor)

    # Guard: compare() can return None when all fallbacks fail
    if result is None:
        result = {}

    result['client_restaurant'] = competitor_service.client_restaurant
    result['competitor_restaurant'] = {
        'name': competitor['name'],
        'address': competitor.get('address', ''),
        'rating': competitor.get('rating', 0),
        'distance_miles': competitor.get('distance_miles', 0),
        'price_category': competitor.get('price_category', '$$'),
    }

    # Data Sources — lets the user verify exactly where prices came from
    from services.gemini_service import get_source_registry
    registry: dict[str, list[dict[str, Any]]] = get_source_registry()

    result['data_sources'] = {
        'client': _build_source_info(
            competitor_service.client_restaurant,
            client_data.get('menu') or [],
            registry,
        ),
        'competitor': _build_source_info(
            competitor,
            competitor.get('menu') or [],
            registry,
        ),
        'registry_url': '/api/data-sources',
    }

    return jsonify(result)


@comparison_bp.route('/api/analysis/recommendations', methods=['GET'])
def recommendations():
    """Get AI-powered market recommendations for the client restaurant."""
    data = competitor_service.find_competitors()
    client_data: dict[str, Any] = {
        **competitor_service.client_restaurant,
        'menu': competitor_service.get_client_menu(),
        'offers': competitor_service.get_client_offers(),
    }
    comp_data: list[dict[str, Any]] = []
    for r in cast(list[dict[str, Any]], data.get('restaurants', []))[:5]:
        r['menu'] = competitor_service.get_restaurant_menu(r)
        r['offers'] = competitor_service.get_restaurant_offers(r)
        comp_data.append(r)

    result = comparison_service.generate_market_analysis(client_data, comp_data)
    return jsonify(result)
