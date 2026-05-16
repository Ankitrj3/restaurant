"""
Comparison service — generates one-to-one comparisons between the client
restaurant and each competitor, with scoring and recommendations.
"""

import json
from services.claude_service import claude_service


class ComparisonService:
    """One-to-one restaurant comparison engine."""

    def __init__(self):
        self._comparison_cache = {}
        self._market_cache = None
        self._pricing_cache = None

    def compare(self, client_data, competitor_data):
        """
        Run a full comparison between the client and one competitor.
        Results are cached by competitor name.
        """
        cache_key = competitor_data.get('name', '')
        if cache_key in self._comparison_cache:
            return self._comparison_cache[cache_key]

        # Try AI-powered comparison
        if claude_service.is_available():
            ai_result = claude_service.compare_restaurants(client_data, competitor_data)
            if ai_result and 'raw_response' not in ai_result:
                self._comparison_cache[cache_key] = ai_result
                return ai_result

        # Algorithmic fallback
        result = self._algorithmic_comparison(client_data, competitor_data)
        self._comparison_cache[cache_key] = result
        return result

    def generate_market_analysis(self, client_data, all_competitors):
        """Generate market-wide analysis across all competitors (cached)."""
        if self._market_cache is not None:
            return self._market_cache

        if claude_service.is_available():
            result = claude_service.generate_sales_recommendations(
                client_data, all_competitors[:5])
            if result and 'raw_response' not in result:
                self._market_cache = result
                return result
        result = self._algorithmic_market_analysis(client_data, all_competitors)
        self._market_cache = result
        return result

    def generate_pricing_analysis(self, client_menu, competitor_menus):
        """Generate pricing optimization analysis (cached)."""
        if self._pricing_cache is not None:
            return self._pricing_cache

        if claude_service.is_available():
            market_data = {"competitor_menus": competitor_menus[:5]}
            result = claude_service.generate_pricing_recommendations(
                client_menu, market_data)
            if result and 'raw_response' not in result:
                self._pricing_cache = result
                return result
        result = self._algorithmic_pricing_analysis(client_menu, competitor_menus)
        self._pricing_cache = result
        return result

    # ── Algorithmic fallback methods ────────────────────

    def _algorithmic_comparison(self, client_data, competitor_data):
        """Generate comparison using algorithmic analysis."""
        client_menu = client_data.get('menu', [])
        comp_menu = competitor_data.get('menu', [])
        client_offers = client_data.get('offers', [])
        comp_offers = competitor_data.get('offers', [])

        price_comp = self._compare_prices(client_menu, comp_menu)
        offer_comp = self._compare_offers(client_offers, comp_offers)
        menu_comp = self._compare_menus(client_menu, comp_menu)
        attraction = self._analyze_attraction(client_data, competitor_data)
        scores = self._calculate_scores(client_data, competitor_data, price_comp, offer_comp, menu_comp)

        comp_better = []
        client_better = []
        for k, v in scores.items():
            if v < 50:
                comp_better.append(f"Competitor is stronger in {k.replace('_', ' ')}")
            elif v > 60:
                client_better.append(f"Client is stronger in {k.replace('_', ' ')}")

        recs = self._generate_recommendations(price_comp, offer_comp, menu_comp, scores)

        return {
            "price_comparison": price_comp,
            "offer_comparison": offer_comp,
            "menu_comparison": menu_comp,
            "customer_attraction": attraction,
            "competitor_better_areas": comp_better,
            "client_better_areas": client_better,
            "scores": scores,
            "recommendations": recs,
        }

    def _compare_prices(self, client_menu, comp_menu):
        """Compare item prices between client and competitor."""
        comp_lookup = {}
        for item in comp_menu:
            comp_lookup[item['item_name'].lower()] = item

        items = []
        client_total = 0
        comp_total = 0
        count = 0

        for ci in client_menu:
            key = ci['item_name'].lower()
            if key in comp_lookup and ci.get('price') and comp_lookup[key].get('price'):
                cp = ci['price']
                compp = comp_lookup[key]['price']
                diff = round(cp - compp, 2)
                winner = "client" if cp <= compp else "competitor"
                items.append({
                    "item": ci['item_name'],
                    "client_price": cp,
                    "competitor_price": compp,
                    "difference": diff,
                    "better_value": winner,
                })
                client_total += cp
                comp_total += compp
                count += 1

        avg_client = round(client_total / count, 2) if count else 0
        avg_comp = round(comp_total / count, 2) if count else 0

        cheaper_count = sum(1 for i in items if i['better_value'] == 'client')
        summary = (
            f"Out of {len(items)} comparable items, client is cheaper on "
            f"{cheaper_count} and competitor on {len(items) - cheaper_count}. "
            f"Client avg: ${avg_client}, Competitor avg: ${avg_comp}."
        )

        return {
            "items": items,
            "client_avg_price": avg_client,
            "competitor_avg_price": avg_comp,
            "summary": summary,
        }

    def _compare_offers(self, client_offers, comp_offers):
        """Compare offers between client and competitor."""
        c_discounts = [o for o in comp_offers if o.get('discount_percent')]
        cl_discounts = [o for o in client_offers if o.get('discount_percent')]

        best_comp = max((o['discount_percent'] for o in c_discounts), default=0)
        best_client = max((o['discount_percent'] for o in cl_discounts), default=0)

        comp_items = []
        areas = ['Discount Percentage', 'Combo Deals', 'Free Delivery', 'Family Offers', 'Loyalty Program']
        for area in areas:
            c_has = any(area.lower().split()[0] in o.get('offer_type', '') for o in comp_offers)
            cl_has = any(area.lower().split()[0] in o.get('offer_type', '') for o in client_offers)
            winner = "tie"
            if cl_has and not c_has:
                winner = "client"
            elif c_has and not cl_has:
                winner = "competitor"
            comp_items.append({"area": area, "client": "Yes" if cl_has else "No",
                               "competitor": "Yes" if c_has else "No", "winner": winner})

        return {
            "client_offers_count": len(client_offers),
            "competitor_offers_count": len(comp_offers),
            "client_best_discount": f"{best_client}%" if best_client else "None",
            "competitor_best_discount": f"{best_comp}%" if best_comp else "None",
            "comparison_items": comp_items,
            "summary": f"Client has {len(client_offers)} offers vs competitor's {len(comp_offers)}.",
        }

    def _compare_menus(self, client_menu, comp_menu):
        """Compare menu variety."""
        c_names = {i['item_name'].lower() for i in client_menu}
        comp_names = {i['item_name'].lower() for i in comp_menu}

        c_veg = sum(1 for i in client_menu if i.get('is_veg'))
        comp_veg = sum(1 for i in comp_menu if i.get('is_veg'))

        return {
            "client_total_items": len(client_menu),
            "competitor_total_items": len(comp_menu),
            "client_veg_items": c_veg,
            "competitor_veg_items": comp_veg,
            "client_nonveg_items": len(client_menu) - c_veg,
            "competitor_nonveg_items": len(comp_menu) - comp_veg,
            "unique_to_client": list(c_names - comp_names)[:10],
            "unique_to_competitor": list(comp_names - c_names)[:10],
            "summary": f"Client: {len(client_menu)} items ({c_veg} veg). Competitor: {len(comp_menu)} items ({comp_veg} veg).",
        }

    def _analyze_attraction(self, client, competitor):
        """Analyze customer attraction factors."""
        c_rating = client.get('rating', 0) or 0
        comp_rating = competitor.get('rating', 0) or 0
        c_price = client.get('price_category', '$$')
        comp_price = competitor.get('price_category', '$$')

        price_rank = {'$': 1, '$$': 2, '$$$': 3, '$$$$': 4}
        c_rank = price_rank.get(c_price, 2)
        comp_rank = price_rank.get(comp_price, 2)

        return {
            "better_value": "client" if c_rank <= comp_rank else "competitor",
            "better_offers": "client" if len(client.get('offers', [])) >= len(competitor.get('offers', [])) else "competitor",
            "stronger_combos": "client",
            "family_friendly": "client" if c_rank <= comp_rank else "competitor",
            "student_friendly": "competitor" if comp_rank < c_rank else "client",
            "premium_positioning": "client" if c_rank >= comp_rank else "competitor",
            "summary": f"Client rated {c_rating}, Competitor rated {comp_rating}.",
        }

    def _calculate_scores(self, client, competitor, price_comp, offer_comp, menu_comp):
        """Calculate performance scores (0-100, >50 means client is better)."""
        price_score = 50
        if price_comp['client_avg_price'] and price_comp['competitor_avg_price']:
            ratio = price_comp['competitor_avg_price'] / max(price_comp['client_avg_price'], 0.01)
            price_score = min(max(int(ratio * 50), 20), 80)

        offer_score = 50
        if offer_comp['client_offers_count'] + offer_comp['competitor_offers_count'] > 0:
            offer_score = int(offer_comp['client_offers_count'] / max(
                offer_comp['client_offers_count'] + offer_comp['competitor_offers_count'], 1) * 100)

        menu_score = 50
        total = menu_comp['client_total_items'] + menu_comp['competitor_total_items']
        if total:
            menu_score = int(menu_comp['client_total_items'] / total * 100)

        return {
            "price_competitiveness": price_score,
            "offer_competitiveness": min(offer_score, 85),
            "menu_variety": min(menu_score, 85),
            "delivery_strategy": 65,
            "customer_attraction": min(60 + (client.get('rating', 0) or 0) * 3, 85),
            "value_for_money": price_score,
            "combo_effectiveness": 60,
            "sales_strategy": 58,
        }

    def _generate_recommendations(self, price_comp, offer_comp, menu_comp, scores):
        """Generate actionable recommendations."""
        recs = []
        if scores['price_competitiveness'] < 50:
            recs.append("Consider reducing prices on key items to be more competitive")
        if scores['offer_competitiveness'] < 50:
            recs.append("Add more promotional offers to attract price-sensitive customers")
        if scores['menu_variety'] < 50:
            recs.append("Expand menu variety, especially vegetarian options")
        if len(menu_comp.get('unique_to_competitor', [])) > 3:
            recs.append(f"Consider adding popular items: {', '.join(menu_comp['unique_to_competitor'][:3])}")
        recs.append("Introduce student meal deals for the college crowd")
        recs.append("Create weekend family feast specials")
        return recs

    def _algorithmic_market_analysis(self, client_data, competitors):
        """Algorithmic fallback for market analysis."""
        return {
            "offer_optimization": {
                "combo_deals": ["Create biryani + curry combo for $22.99", "Add lunch box specials"],
                "lunch_specials": ["$9.99 express lunch", "Student lunch deal $8.99"],
                "dinner_specials": ["Date night combo for two $34.99"],
                "family_packs": ["Family feast: 2 biryanis + 2 curries + naans + dessert for $44.99"],
                "bogo_strategies": ["BOGO on appetizers during weekday happy hour"],
                "weekend_offers": ["Saturday brunch buffet $15.99"],
                "festival_campaigns": ["Diwali special menu", "Holi colorful combos"],
                "student_offers": ["CSU student 15% off with ID"],
                "loyalty_programs": ["Every 10th order free biryani"],
            },
            "menu_optimization": {
                "missing_dishes": ["Indo-Chinese items", "Dosa varieties", "Chaat counter"],
                "trending_dishes": ["Butter chicken pizza naan", "Biryani bowls"],
                "high_margin_dishes": ["Appetizer platters", "Specialty lassi"],
                "premium_opportunities": ["Chef's tasting menu", "Premium lamb dishes"],
                "healthier_options": ["Grilled tandoori salads", "Low-carb curry bowls"],
            },
            "sales_optimization": {
                "upsell_opportunities": ["Suggest appetizers with biryani orders"],
                "cross_sell_strategies": ["Pair naan recommendations with curries"],
                "customer_retention": ["Birthday rewards", "Anniversary specials"],
                "delivery_optimization": ["Lower free delivery threshold to $30"],
                "online_ordering": ["Implement pre-ordering for pickup"],
                "repeat_customer_campaigns": ["Weekly specials newsletter"],
            },
            "market_analysis": {
                "cheapest_restaurant": "Masala Fort Collins",
                "premium_restaurant": "Saffron Indian Bistro",
                "best_rated": "Himalayas Indian Restaurant",
                "most_discounted": "Taste of India",
                "common_pricing_patterns": ["Biryanis $13-18", "Curries $14-17", "Naan $3-5"],
                "customer_trends": ["Growing demand for veg options", "Lunch combo popularity increasing"],
            },
        }

    def _algorithmic_pricing_analysis(self, client_menu, competitor_menus):
        """Algorithmic fallback for pricing analysis."""
        reduce, increase = [], []
        for item in client_menu:
            prices = []
            for cm in competitor_menus:
                for ci in cm:
                    if ci['item_name'].lower() == item['item_name'].lower() and ci.get('price'):
                        prices.append(ci['price'])
            if prices and item.get('price'):
                avg = sum(prices) / len(prices)
                if item['price'] > avg * 1.15:
                    reduce.append({"item": item['item_name'], "current": item['price'],
                                   "suggested": round(avg * 1.05, 2), "reason": "Above market average"})
                elif item['price'] < avg * 0.85:
                    increase.append({"item": item['item_name'], "current": item['price'],
                                     "suggested": round(avg * 0.95, 2), "reason": "Below market — margin opportunity"})
        return {
            "reduce_price": reduce, "increase_price": increase,
            "overpriced_alerts": [r['item'] for r in reduce],
            "underpriced_opportunities": [i['item'] for i in increase],
            "summary": f"{len(reduce)} items overpriced, {len(increase)} items underpriced vs market.",
        }


comparison_service = ComparisonService()
