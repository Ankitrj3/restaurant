"""
Market Matrix Service — orchestrates the full market intelligence pipeline.

Implements ALL requested algorithms:
  § 3.1 — Category Segmentation (5 standard categories)
  § 3.2 — Competing Column Capture Rule (null + "Not Present at Our Store")
  § 3.3 — String Alignment Filter (rapidfuzz similarity metric)
  § 4.1 — Cross-Platform Price Variance ΔP = ((P_app - P_instore) / P_instore) × 100
  § 4.2 — Basket Revenue Subsidy Logic ($15 threshold → boolean flag)
  
  OPTIMIZATION ALGORITHMS:
  § OPT-1 — Price Optimization: weighted competitor avg → optimal price recommendation
  § OPT-2 — Competitive Gap Analysis: per-item price gap % with strategic flags
  § OPT-3 — Category Market Position: dominance score per category
  § OPT-4 — Platform Arbitrage Detection: best/worst platform + spread %
  § OPT-5 — Revenue Impact Estimator: projected monthly revenue delta
"""

import json
import time
import math
from datetime import datetime, timezone
from config import Config
from services.matching_service import matching_service


# ── Constants ──────────────────────────────────────────────
FREE_DELIVERY_THRESHOLD = 15.0
STANDARD_CATEGORIES = ['Biryani', 'Curries', 'Starter', 'Tandoori', 'Dessert']

# Optimization parameters
MARGIN_FLOOR_PCT = 0.05          # 5% minimum margin protection
PRICE_ELASTICITY_FACTOR = -1.2   # Estimated price elasticity for Indian food
AVG_MONTHLY_ORDERS_PER_ITEM = 45 # Estimated average monthly orders per item


class MarketMatrixService:
    """Generates a unified market intelligence JSON matrix with optimization."""

    def __init__(self):
        self._cache = None
        self._cache_ts = 0
        self._CACHE_TTL = 3600  # 1 hour

    def generate_matrix(self, radius_miles=10.0):
        """Main entry point — generates the full market matrix JSON.
        
        Pipeline steps:
        1. Discovery — find competitors via Gemini grounded search
        2. Data Collection — fetch menus across all 4 platforms
        3. § 3.1 Categorization — map dishes to standard categories
        4. § 3.3 Fuzzy Matching — align dish names across restaurants
        5. § 3.2 Competing Column Capture — null fields + "Not Present" flags
        6. § 4.1 ΔP Price Variance — cross-platform markup computation
        7. § 4.2 Basket Revenue Subsidy — $15 threshold boolean
        8. § OPT-1→5 Optimization — price/gap/position/arbitrage/revenue
        9. Assembly — build the enforced JSON schema
        """
        # Check cache
        now = time.time()
        if self._cache and (now - self._cache_ts) < self._CACHE_TTL:
            print("[MarketMatrix] Returning cached matrix")
            return self._cache

        print(f"[MarketMatrix] Starting full market scan (radius={radius_miles}mi)...")
        start = time.time()

        # ── Step 1: Try optimized single-call approach first ──
        raw_data = self._fetch_full_market_data(radius_miles)

        if raw_data:
            result = self._build_matrix_from_full_data(raw_data, radius_miles)
        else:
            # ── Fallback: Multi-call approach ──
            print("[MarketMatrix] Full market data call failed, using multi-call approach")
            result = self._build_matrix_multi_call(radius_miles)

        # ── Step 8: Run optimization algorithms on the assembled matrix ──
        result["optimization"] = self._run_optimization_suite(result.get("matrix", []))

        elapsed = round(time.time() - start, 1)
        print(f"[MarketMatrix] Matrix generated in {elapsed}s — {len(result.get('matrix', []))} items")

        self._cache = result
        self._cache_ts = time.time()
        return result

    def _fetch_full_market_data(self, radius_miles):
        """Attempt single comprehensive Gemini grounded call."""
        try:
            from services.gemini_service import gemini_service
            if not gemini_service.is_available():
                return None

            result = gemini_service.fetch_full_market_data(
                Config.CLIENT_LAT, Config.CLIENT_LNG, radius_miles,
                Config.CLIENT_RESTAURANT_NAME, Config.CLIENT_RESTAURANT_ADDRESS
            )
            if result and isinstance(result, dict):
                # Validate minimum data
                target = result.get('target_restaurant', {})
                competitors = result.get('competitors', [])
                if target.get('instore_menu') or competitors:
                    print(f"[MarketMatrix] Full data: {len(competitors)} competitors found")
                    return result
        except Exception as e:
            print(f"[MarketMatrix] Full data fetch error: {e}")
        return None

    def _build_matrix_from_full_data(self, raw_data, radius_miles):
        """Build the output JSON from the comprehensive Gemini response."""
        target = raw_data.get('target_restaurant', {})
        competitors = raw_data.get('competitors', [])
        delivery_fees_raw = raw_data.get('delivery_fees', [])

        # Build Bawarchi pricing lookup
        bawarchi_instore = self._menu_to_dict(target.get('instore_menu', []))
        bawarchi_uber = self._menu_to_dict(target.get('ubereats_menu', []))
        bawarchi_dd = self._menu_to_dict(target.get('doordash_menu', []))
        bawarchi_gh = self._menu_to_dict(target.get('grubhub_menu', []))

        matrix = []

        # Process each competitor
        for comp in competitors:
            comp_name = comp.get('name', 'Unknown Competitor')
            comp_instore = self._menu_to_dict(comp.get('instore_menu', []))
            comp_uber = self._menu_to_dict(comp.get('ubereats_menu', []))
            comp_dd = self._menu_to_dict(comp.get('doordash_menu', []))
            comp_gh = self._menu_to_dict(comp.get('grubhub_menu', []))

            # Union of all dishes across both restaurants
            all_dishes = set()
            for d in list(bawarchi_instore.keys()) + list(bawarchi_uber.keys()) + \
                       list(bawarchi_dd.keys()) + list(bawarchi_gh.keys()) + \
                       list(comp_instore.keys()) + list(comp_uber.keys()) + \
                       list(comp_dd.keys()) + list(comp_gh.keys()):
                all_dishes.add(d)

            # Deduplicate via fuzzy matching
            canonical_map = self._build_canonical_map(all_dishes)

            for canonical, variants in canonical_map.items():
                # Get prices for Bawarchi
                b_instore = self._find_price(variants, bawarchi_instore)
                b_uber = self._find_price(variants, bawarchi_uber)
                b_dd = self._find_price(variants, bawarchi_dd)
                b_gh = self._find_price(variants, bawarchi_gh)

                # Get prices for competitor
                c_instore = self._find_price(variants, comp_instore)
                c_uber = self._find_price(variants, comp_uber)
                c_dd = self._find_price(variants, comp_dd)
                c_gh = self._find_price(variants, comp_gh)

                # Determine presence
                is_at_bawarchi = any(p is not None for p in [b_instore, b_uber, b_dd, b_gh])
                is_at_competitor = any(p is not None for p in [c_instore, c_uber, c_dd, c_gh])

                # Category
                category = matching_service.categorize_dish(canonical)

                # Compute markups
                b_uber_markup = self._calc_markup(b_uber, b_instore)
                b_dd_markup = self._calc_markup(b_dd, b_instore)
                b_gh_markup = self._calc_markup(b_gh, b_instore)
                c_uber_markup = self._calc_markup(c_uber, c_instore)
                c_dd_markup = self._calc_markup(c_dd, c_instore)
                c_gh_markup = self._calc_markup(c_gh, c_instore)

                # Delivery threshold
                ref_price = b_instore or c_instore or b_uber or c_uber
                meets_threshold = ref_price > FREE_DELIVERY_THRESHOLD if ref_price else False

                entry = {
                    "category": category,
                    "dish_canonical": canonical,
                    "bawarchi": {
                        "instore": b_instore if is_at_bawarchi else None,
                        "uber_eats": b_uber if is_at_bawarchi else None,
                        "door_dash": b_dd if is_at_bawarchi else None,
                        "grubhub": b_gh if is_at_bawarchi else None
                    },
                    "competitor": {
                        "name": comp_name,
                        "instore": c_instore if is_at_competitor else None,
                        "uber_eats": c_uber if is_at_competitor else None,
                        "door_dash": c_dd if is_at_competitor else None,
                        "grubhub": c_gh if is_at_competitor else None
                    },
                    "metrics": {
                        "is_present_at_bawarchi": is_at_bawarchi,
                        "is_present_at_competitor": is_at_competitor,
                        "bawarchi_uber_markup_pct": b_uber_markup,
                        "bawarchi_doordash_markup_pct": b_dd_markup,
                        "bawarchi_grubhub_markup_pct": b_gh_markup,
                        "competitor_uber_markup_pct": c_uber_markup,
                        "competitor_doordash_markup_pct": c_dd_markup,
                        "competitor_grubhub_markup_pct": c_gh_markup,
                        "meets_free_delivery_threshold": meets_threshold
                    }
                }

                # Add "Not Present" flags
                if not is_at_bawarchi:
                    entry["bawarchi"]["status"] = "Not Present at Our Store"
                if not is_at_competitor:
                    entry["competitor"]["status"] = f"Not Present at {comp_name}"

                matrix.append(entry)

        # Build logistics comparison
        logistics = self._build_logistics(delivery_fees_raw)

        return {
            "market_center": Config.CLIENT_RESTAURANT_NAME,
            "radius_limit_miles": radius_miles,
            "system_timestamp_2026": datetime.now(timezone.utc).isoformat(),
            "matrix": sorted(matrix, key=lambda x: (
                STANDARD_CATEGORIES.index(x['category']) if x['category'] in STANDARD_CATEGORIES else 99,
                x['dish_canonical']
            )),
            "logistics_comparison": logistics
        }

    def _build_matrix_multi_call(self, radius_miles):
        """Fallback: Build matrix using individual platform adapter calls."""
        from services.competitor_service import competitor_service
        from services.platform_service import platform_service

        # Discover competitors
        discovery = competitor_service.find_competitors(max_radius=radius_miles)
        restaurants = discovery.get('restaurants', [])

        client_name = Config.CLIENT_RESTAURANT_NAME
        matrix = []
        logistics = []

        # Get Bawarchi menus across platforms
        b_instore = self._list_to_dict(platform_service.get_platform_menu(client_name, 'instore'))
        b_uber = self._list_to_dict(platform_service.get_platform_menu(client_name, 'ubereats'))
        b_dd = self._list_to_dict(platform_service.get_platform_menu(client_name, 'doordash'))
        b_gh = self._list_to_dict(platform_service.get_platform_menu(client_name, 'grubhub'))

        # Bawarchi delivery fees
        b_ub_fees = platform_service.get_platform_delivery_fees(client_name, 'ubereats')
        b_dd_fees = platform_service.get_platform_delivery_fees(client_name, 'doordash')
        b_gh_fees = platform_service.get_platform_delivery_fees(client_name, 'grubhub')

        logistics.append({
            "restaurant_name": client_name,
            "uber_delivery_fee": b_ub_fees.get('delivery_fee'),
            "doordash_delivery_fee": b_dd_fees.get('delivery_fee'),
            "grubhub_delivery_fee": b_gh_fees.get('delivery_fee'),
            "has_free_delivery_over_15_promo": any(
                (f.get('free_delivery_threshold') or 99) <= FREE_DELIVERY_THRESHOLD
                for f in [b_ub_fees, b_dd_fees, b_gh_fees]
            )
        })

        for comp in restaurants:
            comp_name = comp.get('name', 'Unknown')

            # Get competitor menus
            c_instore = self._list_to_dict(platform_service.get_platform_menu(comp_name, 'instore'))
            c_uber = self._list_to_dict(platform_service.get_platform_menu(comp_name, 'ubereats'))
            c_dd = self._list_to_dict(platform_service.get_platform_menu(comp_name, 'doordash'))
            c_gh = self._list_to_dict(platform_service.get_platform_menu(comp_name, 'grubhub'))

            # Competitor delivery fees
            c_ub_fees = platform_service.get_platform_delivery_fees(comp_name, 'ubereats')
            c_dd_fees = platform_service.get_platform_delivery_fees(comp_name, 'doordash')
            c_gh_fees = platform_service.get_platform_delivery_fees(comp_name, 'grubhub')

            logistics.append({
                "restaurant_name": comp_name,
                "uber_delivery_fee": c_ub_fees.get('delivery_fee'),
                "doordash_delivery_fee": c_dd_fees.get('delivery_fee'),
                "grubhub_delivery_fee": c_gh_fees.get('delivery_fee'),
                "has_free_delivery_over_15_promo": any(
                    (f.get('free_delivery_threshold') or 99) <= FREE_DELIVERY_THRESHOLD
                    for f in [c_ub_fees, c_dd_fees, c_gh_fees]
                )
            })

            # Union all dish names
            all_dishes = set()
            for d in list(b_instore.keys()) + list(b_uber.keys()) + \
                       list(b_dd.keys()) + list(b_gh.keys()) + \
                       list(c_instore.keys()) + list(c_uber.keys()) + \
                       list(c_dd.keys()) + list(c_gh.keys()):
                all_dishes.add(d)

            canonical_map = self._build_canonical_map(all_dishes)

            for canonical, variants in canonical_map.items():
                bi = self._find_price(variants, b_instore)
                bu = self._find_price(variants, b_uber)
                bd = self._find_price(variants, b_dd)
                bg = self._find_price(variants, b_gh)

                ci = self._find_price(variants, c_instore)
                cu = self._find_price(variants, c_uber)
                cd = self._find_price(variants, c_dd)
                cg = self._find_price(variants, c_gh)

                is_at_b = any(p is not None for p in [bi, bu, bd, bg])
                is_at_c = any(p is not None for p in [ci, cu, cd, cg])

                category = matching_service.categorize_dish(canonical)

                entry = {
                    "category": category,
                    "dish_canonical": canonical,
                    "bawarchi": {
                        "instore": bi if is_at_b else None,
                        "uber_eats": bu if is_at_b else None,
                        "door_dash": bd if is_at_b else None,
                        "grubhub": bg if is_at_b else None
                    },
                    "competitor": {
                        "name": comp_name,
                        "instore": ci if is_at_c else None,
                        "uber_eats": cu if is_at_c else None,
                        "door_dash": cd if is_at_c else None,
                        "grubhub": cg if is_at_c else None
                    },
                    "metrics": {
                        "is_present_at_bawarchi": is_at_b,
                        "is_present_at_competitor": is_at_c,
                        "bawarchi_uber_markup_pct": self._calc_markup(bu, bi),
                        "bawarchi_doordash_markup_pct": self._calc_markup(bd, bi),
                        "bawarchi_grubhub_markup_pct": self._calc_markup(bg, bi),
                        "competitor_uber_markup_pct": self._calc_markup(cu, ci),
                        "competitor_doordash_markup_pct": self._calc_markup(cd, ci),
                        "competitor_grubhub_markup_pct": self._calc_markup(cg, ci),
                        "meets_free_delivery_threshold": (bi or ci or bu or cu or 0) > FREE_DELIVERY_THRESHOLD
                    }
                }

                if not is_at_b:
                    entry["bawarchi"]["status"] = "Not Present at Our Store"
                if not is_at_c:
                    entry["competitor"]["status"] = f"Not Present at {comp_name}"

                matrix.append(entry)

        return {
            "market_center": Config.CLIENT_RESTAURANT_NAME,
            "radius_limit_miles": radius_miles,
            "system_timestamp_2026": datetime.now(timezone.utc).isoformat(),
            "matrix": sorted(matrix, key=lambda x: (
                STANDARD_CATEGORIES.index(x['category']) if x['category'] in STANDARD_CATEGORIES else 99,
                x['dish_canonical']
            )),
            "logistics_comparison": logistics
        }

    # ── Helper methods ──────────────────────────────────────────

    def _menu_to_dict(self, menu_items):
        """Convert a list of menu item dicts to a name→price dictionary."""
        result = {}
        if not menu_items or not isinstance(menu_items, list):
            return result
        for item in menu_items:
            name = item.get('item_name') or item.get('name', '')
            price = item.get('price')
            if name and price is not None:
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    continue
                result[name.strip()] = price
        return result

    def _list_to_dict(self, menu_list):
        """Convert platform adapter menu list to name→price dict."""
        result = {}
        if not menu_list or not isinstance(menu_list, list):
            return result
        for item in menu_list:
            name = item.get('item_name', '')
            price = item.get('price')
            if name and price is not None:
                result[name.strip()] = float(price) if price else None
        return result

    def _build_canonical_map(self, dish_names):
        """Group dish names by fuzzy similarity into canonical groups.
        Returns { canonical_name: [variant1, variant2, ...] }"""
        canonical_map = {}
        for name in dish_names:
            if not name:
                continue
            matched = False
            for canonical in canonical_map:
                score = matching_service.similarity_score(name, canonical)
                if score >= Config.FUZZY_MATCH_THRESHOLD:
                    canonical_map[canonical].append(name)
                    matched = True
                    break
            if not matched:
                # Use normalized name as canonical
                norm = self._to_title_case(matching_service.normalize_name(name))
                # Check if normalized name already exists
                for canonical in canonical_map:
                    if matching_service.similarity_score(norm, canonical) >= Config.FUZZY_MATCH_THRESHOLD:
                        canonical_map[canonical].append(name)
                        matched = True
                        break
                if not matched:
                    canonical_map[norm or name] = [name]
        return canonical_map

    def _find_price(self, variants, price_dict):
        """Find the price for any variant name in the price dictionary."""
        for variant in variants:
            if variant in price_dict:
                return price_dict[variant]
            # Try fuzzy match against dict keys
            for key in price_dict:
                if matching_service.similarity_score(variant, key) >= Config.FUZZY_MATCH_THRESHOLD:
                    return price_dict[key]
        return None

    def _calc_markup(self, platform_price, instore_price):
        """Calculate markup percentage: ΔP = ((P_delivery - P_instore) / P_instore) × 100"""
        if platform_price is None or instore_price is None or instore_price == 0:
            return None
        return round(((platform_price - instore_price) / instore_price) * 100, 2)

    def _to_title_case(self, normalized_name):
        """Convert normalized lowercase name back to Title Case."""
        if not normalized_name:
            return normalized_name
        return ' '.join(word.capitalize() for word in normalized_name.split())

    def _build_logistics(self, delivery_fees_raw):
        """Build the logistics_comparison array from raw delivery fee data."""
        logistics = []
        if not delivery_fees_raw or not isinstance(delivery_fees_raw, list):
            return logistics
        for entry in delivery_fees_raw:
            logistics.append({
                "restaurant_name": entry.get('restaurant_name', 'Unknown'),
                "uber_delivery_fee": entry.get('uber_delivery_fee'),
                "doordash_delivery_fee": entry.get('doordash_delivery_fee'),
                "grubhub_delivery_fee": entry.get('grubhub_delivery_fee'),
                "has_free_delivery_over_15_promo": entry.get('has_free_delivery_over_15_promo', False)
            })
        return logistics

    # ══════════════════════════════════════════════════════════════
    #  OPTIMIZATION ALGORITHMS (§ OPT-1 through OPT-5)
    # ══════════════════════════════════════════════════════════════

    def _run_optimization_suite(self, matrix):
        """Run all 5 optimization algorithms on the assembled matrix.
        
        Returns a dict with all optimization results appended to the JSON output.
        """
        print("[MarketMatrix] Running optimization suite...")
        return {
            "price_recommendations": self._opt_price_recommendations(matrix),
            "competitive_gap_analysis": self._opt_competitive_gap(matrix),
            "category_market_position": self._opt_category_position(matrix),
            "platform_arbitrage": self._opt_platform_arbitrage(matrix),
            "revenue_impact_estimate": self._opt_revenue_impact(matrix),
        }

    def _opt_price_recommendations(self, matrix):
        """§ OPT-1: Price Optimization Algorithm.
        
        For each item where both Bawarchi and competitor have in-store prices,
        compute the optimal price using a weighted competitor average with
        margin floor protection.
        
        Formula:
            P_optimal = max(P_competitor_avg × (1 - MARGIN_FLOOR), P_bawarchi × 0.95)
            
        If Bawarchi is >10% more expensive, flag as "overpriced".
        If Bawarchi is >10% cheaper, flag as "underpriced" (margin opportunity).
        """
        recommendations = []
        for item in matrix:
            b_price = item.get("bawarchi", {}).get("instore")
            c_price = item.get("competitor", {}).get("instore")
            if b_price is None or c_price is None:
                continue

            # Weighted competitor average (we only have 1 competitor per row,
            # but we weight in-store 60%, platform avg 40% if available)
            platform_prices = []
            for key in ["uber_eats", "door_dash", "grubhub"]:
                cp = item.get("competitor", {}).get(key)
                if cp is not None:
                    platform_prices.append(cp)

            if platform_prices:
                comp_platform_avg = sum(platform_prices) / len(platform_prices)
                weighted_avg = (c_price * 0.6) + (comp_platform_avg * 0.4)
            else:
                weighted_avg = c_price

            # Optimal price: undercut competitor avg by margin floor, but never below 95% of current
            p_optimal = max(
                round(weighted_avg * (1 - MARGIN_FLOOR_PCT), 2),
                round(b_price * 0.95, 2)
            )

            # Price gap
            gap_pct = round(((b_price - c_price) / c_price) * 100, 2) if c_price else 0

            # Strategic flag
            if gap_pct > 10:
                flag = "OVERPRICED"
                action = f"Reduce ${round(b_price - p_optimal, 2)} to ${p_optimal}"
            elif gap_pct < -10:
                flag = "UNDERPRICED"
                action = f"Margin opportunity: raise to ${p_optimal}"
            else:
                flag = "ALIGNED"
                action = "Price is competitive — no change needed"

            recommendations.append({
                "dish": item.get("dish_canonical"),
                "category": item.get("category"),
                "current_price": b_price,
                "competitor_price": c_price,
                "optimal_price": p_optimal,
                "gap_pct": gap_pct,
                "flag": flag,
                "action": action
            })

        return recommendations

    def _opt_competitive_gap(self, matrix):
        """§ OPT-2: Competitive Gap Analysis.
        
        For each item, compute the price gap between Bawarchi and competitor
        across ALL platforms, and produce a strategic flag.
        
        Formula per platform:
            Gap% = ((P_bawarchi - P_competitor) / P_competitor) × 100
        """
        gap_report = []
        for item in matrix:
            if not item.get("metrics", {}).get("is_present_at_bawarchi") or \
               not item.get("metrics", {}).get("is_present_at_competitor"):
                continue

            gaps = {}
            for platform_key in ["instore", "uber_eats", "door_dash", "grubhub"]:
                b_p = item.get("bawarchi", {}).get(platform_key)
                c_p = item.get("competitor", {}).get(platform_key)
                if b_p is not None and c_p is not None and c_p > 0:
                    gaps[platform_key] = round(((b_p - c_p) / c_p) * 100, 2)

            if not gaps:
                continue

            avg_gap = round(sum(gaps.values()) / len(gaps), 2)

            # Strategic classification
            if avg_gap > 15:
                strategy = "PREMIUM_RISK"
                recommendation = "Significant price premium — risk of customer loss"
            elif avg_gap > 5:
                strategy = "SLIGHT_PREMIUM"
                recommendation = "Marginally above competitor — monitor closely"
            elif avg_gap > -5:
                strategy = "COMPETITIVE"
                recommendation = "Well-aligned with market — maintain position"
            elif avg_gap > -15:
                strategy = "VALUE_LEADER"
                recommendation = "Below competitor — strong value proposition"
            else:
                strategy = "DEEP_UNDERCUT"
                recommendation = "Significantly below market — review for margin leakage"

            gap_report.append({
                "dish": item.get("dish_canonical"),
                "category": item.get("category"),
                "competitor_name": item.get("competitor", {}).get("name"),
                "platform_gaps": gaps,
                "avg_gap_pct": avg_gap,
                "strategy": strategy,
                "recommendation": recommendation
            })

        return gap_report

    def _opt_category_position(self, matrix):
        """§ OPT-3: Category Market Position Analysis.
        
        Compute Bawarchi's average price vs competitor average price
        per category, and produce a dominance score.
        
        Dominance Score = (Competitor_Avg - Bawarchi_Avg) / Competitor_Avg × 100
        Positive = Bawarchi is cheaper (dominant), Negative = Bawarchi is pricier
        """
        category_data = {}
        for item in matrix:
            cat = item.get("category", "Other")
            if cat not in category_data:
                category_data[cat] = {
                    "bawarchi_prices": [], "competitor_prices": [],
                    "bawarchi_items": 0, "competitor_items": 0,
                    "both_present": 0
                }

            b_price = item.get("bawarchi", {}).get("instore")
            c_price = item.get("competitor", {}).get("instore")

            if b_price is not None:
                category_data[cat]["bawarchi_prices"].append(b_price)
                category_data[cat]["bawarchi_items"] += 1
            if c_price is not None:
                category_data[cat]["competitor_prices"].append(c_price)
                category_data[cat]["competitor_items"] += 1
            if b_price is not None and c_price is not None:
                category_data[cat]["both_present"] += 1

        positions = []
        for cat in STANDARD_CATEGORIES + [c for c in category_data if c not in STANDARD_CATEGORIES]:
            if cat not in category_data:
                continue
            d = category_data[cat]
            b_avg = round(sum(d["bawarchi_prices"]) / len(d["bawarchi_prices"]), 2) if d["bawarchi_prices"] else None
            c_avg = round(sum(d["competitor_prices"]) / len(d["competitor_prices"]), 2) if d["competitor_prices"] else None

            if b_avg and c_avg and c_avg > 0:
                dominance = round(((c_avg - b_avg) / c_avg) * 100, 2)
            else:
                dominance = None

            # Market position label
            if dominance is None:
                position = "INSUFFICIENT_DATA"
            elif dominance > 10:
                position = "PRICE_LEADER"
            elif dominance > 0:
                position = "COMPETITIVE"
            elif dominance > -10:
                position = "AT_PARITY"
            else:
                position = "PREMIUM_PRICED"

            positions.append({
                "category": cat,
                "bawarchi_avg_price": b_avg,
                "competitor_avg_price": c_avg,
                "bawarchi_item_count": d["bawarchi_items"],
                "competitor_item_count": d["competitor_items"],
                "overlapping_items": d["both_present"],
                "dominance_score": dominance,
                "market_position": position
            })

        return positions

    def _opt_platform_arbitrage(self, matrix):
        """§ OPT-4: Platform Arbitrage Detection.
        
        For each item, find the cheapest and most expensive platform,
        compute the cross-platform spread, and flag arbitrage opportunities.
        
        Spread% = ((P_max - P_min) / P_min) × 100
        """
        arbitrage = []
        for item in matrix:
            if not item.get("metrics", {}).get("is_present_at_bawarchi"):
                continue

            platforms = {}
            for key, label in [("instore", "In-Store"), ("uber_eats", "UberEats"),
                               ("door_dash", "DoorDash"), ("grubhub", "Grubhub")]:
                p = item.get("bawarchi", {}).get(key)
                if p is not None:
                    platforms[label] = p

            if len(platforms) < 2:
                continue

            cheapest = min(platforms, key=platforms.get)
            most_expensive = max(platforms, key=platforms.get)
            p_min = platforms[cheapest]
            p_max = platforms[most_expensive]
            spread = round(((p_max - p_min) / p_min) * 100, 2) if p_min > 0 else 0

            # Flag high-spread items
            if spread > 30:
                alert = "HIGH_SPREAD"
                note = f"${p_max - p_min:.2f} gap between {cheapest} and {most_expensive}"
            elif spread > 15:
                alert = "MODERATE_SPREAD"
                note = "Normal platform markup range"
            else:
                alert = "LOW_SPREAD"
                note = "Tight cross-platform pricing"

            arbitrage.append({
                "dish": item.get("dish_canonical"),
                "category": item.get("category"),
                "cheapest_platform": cheapest,
                "cheapest_price": p_min,
                "most_expensive_platform": most_expensive,
                "most_expensive_price": p_max,
                "spread_pct": spread,
                "alert": alert,
                "note": note,
                "all_platform_prices": platforms
            })

        # Sort by spread descending (biggest arbitrage opportunities first)
        return sorted(arbitrage, key=lambda x: x["spread_pct"], reverse=True)

    def _opt_revenue_impact(self, matrix):
        """§ OPT-5: Revenue Impact Estimator.
        
        For each item where an optimal price differs from current price,
        estimate the monthly revenue impact using a price elasticity model.
        
        Formulas:
            ΔP% = (P_optimal - P_current) / P_current
            ΔQ% = ΔP% × Price_Elasticity_Factor (negative = price up → demand down)
            New_Orders = Current_Orders × (1 + ΔQ%)
            Revenue_Current = P_current × Current_Orders
            Revenue_New = P_optimal × New_Orders
            Monthly_Delta = Revenue_New - Revenue_Current
        """
        price_recs = self._opt_price_recommendations(matrix)
        impacts = []
        total_revenue_current = 0
        total_revenue_optimized = 0

        for rec in price_recs:
            if rec["flag"] == "ALIGNED":
                continue

            p_current = rec["current_price"]
            p_optimal = rec["optimal_price"]
            if p_current == 0:
                continue

            # Price change percentage
            delta_p_pct = (p_optimal - p_current) / p_current

            # Demand change (price elasticity model)
            delta_q_pct = delta_p_pct * PRICE_ELASTICITY_FACTOR

            # Revenue calculations
            current_orders = AVG_MONTHLY_ORDERS_PER_ITEM
            new_orders = max(1, round(current_orders * (1 + delta_q_pct)))
            rev_current = round(p_current * current_orders, 2)
            rev_new = round(p_optimal * new_orders, 2)
            monthly_delta = round(rev_new - rev_current, 2)

            total_revenue_current += rev_current
            total_revenue_optimized += rev_new

            impacts.append({
                "dish": rec["dish"],
                "category": rec["category"],
                "current_price": p_current,
                "optimal_price": p_optimal,
                "price_change_pct": round(delta_p_pct * 100, 2),
                "demand_change_pct": round(delta_q_pct * 100, 2),
                "current_monthly_orders": current_orders,
                "projected_monthly_orders": new_orders,
                "current_monthly_revenue": rev_current,
                "projected_monthly_revenue": rev_new,
                "monthly_revenue_delta": monthly_delta,
                "flag": rec["flag"]
            })

        return {
            "item_impacts": impacts,
            "summary": {
                "items_analyzed": len(impacts),
                "total_current_monthly_revenue": round(total_revenue_current, 2),
                "total_optimized_monthly_revenue": round(total_revenue_optimized, 2),
                "total_monthly_revenue_delta": round(total_revenue_optimized - total_revenue_current, 2),
                "price_elasticity_used": PRICE_ELASTICITY_FACTOR,
                "avg_monthly_orders_assumed": AVG_MONTHLY_ORDERS_PER_ITEM
            }
        }


# Singleton
market_matrix_service = MarketMatrixService()

