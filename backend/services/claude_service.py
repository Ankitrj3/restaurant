"""
Claude AI service for intelligent menu extraction, pricing analysis,
competitor comparison, and recommendation generation.
"""

import json
from config import Config

try:
    import anthropic
    import httpx
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
class ClaudeService:
    """AI-powered analysis engine using Claude API."""

    def __init__(self):
        self.api_key = Config.ANTHROPIC_API_KEY
        self.client = None
        if HAS_ANTHROPIC and self.api_key:
            http_client = httpx.Client(verify=False)
            self.client = anthropic.Anthropic(api_key=self.api_key, http_client=http_client)
        self.model = "claude-3-5-sonnet-20241022"

    def is_available(self):
        return self.client is not None

    def _ask(self, system_prompt, user_prompt, max_tokens=4096):
        """Send a prompt to Claude and return the parsed JSON response."""
        if not self.is_available():
            return None
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = response.content[0].text
            # Try to extract JSON from the response
            try:
                start = text.index('{')
                end = text.rindex('}') + 1
                return json.loads(text[start:end])
            except (ValueError, json.JSONDecodeError):
                try:
                    start = text.index('[')
                    end = text.rindex(']') + 1
                    return json.loads(text[start:end])
                except (ValueError, json.JSONDecodeError):
                    return {"raw_response": text}
        except Exception as e:
            print(f"[Claude] API error: {e}")
            return None

    def extract_menu_from_text(self, raw_text, restaurant_name):
        """Use Claude to extract structured menu data from raw scraped text."""
        system = (
            "You are an expert at extracting restaurant menu data. "
            "Return ONLY valid JSON. No explanations."
        )
        prompt = f"""Extract the complete menu from this restaurant content for "{restaurant_name}".

Return JSON with this structure:
{{
  "items": [
    {{
      "item_name": "string",
      "category": "Biryani|Curry|Tandoori|Appetizer|Naan|Rice|Dessert|Drink|Combo|Lunch Special|Dinner Special|Family Pack|Kids Meal|Other",
      "description": "string or null",
      "price": number_or_null,
      "is_veg": true_or_false,
      "is_popular": true_or_false,
      "is_signature": true_or_false,
      "is_bestseller": true_or_false,
      "spice_level": "Mild|Medium|Hot|Extra Hot|null"
    }}
  ]
}}

Raw content:
{raw_text[:8000]}"""
        return self._ask(system, prompt)

    def extract_offers_from_text(self, raw_text, restaurant_name):
        """Use Claude to extract structured offers from raw scraped text."""
        system = "You are an expert at extracting restaurant promotions and offers. Return ONLY valid JSON."
        prompt = f"""Extract all offers, promotions, and deals for "{restaurant_name}".

Return JSON:
{{
  "offers": [
    {{
      "offer_type": "coupon|bogo|combo|discount|free_delivery|loyalty|festival|student|referral",
      "title": "string",
      "description": "string",
      "discount_percent": number_or_null,
      "discount_amount": number_or_null,
      "min_order_amount": number_or_null,
      "code": "string or null",
      "platform": "UberEats|DoorDash|Grubhub|Website|All"
    }}
  ]
}}

Raw content:
{raw_text[:5000]}"""
        return self._ask(system, prompt)

    def infer_restaurant_website(self, restaurant_name, restaurant_address):
        """Ask Claude to infer the official website URL from name/address."""
        system = (
            "You are a search assistant. Return ONLY valid JSON. "
            "If unsure, return null for website_url."
        )
        prompt = f"""Find the official website URL for this restaurant.

Restaurant name: {restaurant_name}
Address: {restaurant_address}

Return JSON:
{{
  "website_url": "https://example.com" | null
}}
"""
        return self._ask(system, prompt, max_tokens=512)

    def compare_restaurants(self, client_data, competitor_data):
        """Generate a detailed one-to-one comparison between client and competitor."""
        system = (
            "You are a restaurant business intelligence analyst specializing in Indian cuisine. "
            "Provide detailed, actionable comparison analysis. Return ONLY valid JSON."
        )
        prompt = f"""Compare these two Indian restaurants:

CLIENT RESTAURANT: {json.dumps(client_data, default=str)[:4000]}

COMPETITOR RESTAURANT: {json.dumps(competitor_data, default=str)[:4000]}

Return JSON:
{{
  "price_comparison": {{
    "items": [
      {{"item": "Chicken Biryani", "client_price": 14.99, "competitor_price": 12.99, "difference": 2.00, "better_value": "competitor"}}
    ],
    "client_avg_price": 0, "competitor_avg_price": 0,
    "summary": "string"
  }},
  "offer_comparison": {{
    "client_offers_count": 0, "competitor_offers_count": 0,
    "client_best_discount": "", "competitor_best_discount": "",
    "comparison_items": [{{"area": "", "client": "", "competitor": "", "winner": ""}}],
    "summary": "string"
  }},
  "menu_comparison": {{
    "client_total_items": 0, "competitor_total_items": 0,
    "client_veg_items": 0, "competitor_veg_items": 0,
    "client_nonveg_items": 0, "competitor_nonveg_items": 0,
    "unique_to_client": [], "unique_to_competitor": [],
    "summary": "string"
  }},
  "customer_attraction": {{
    "better_value": "", "better_offers": "", "stronger_combos": "",
    "family_friendly": "", "student_friendly": "", "premium_positioning": "",
    "summary": "string"
  }},
  "competitor_better_areas": ["string"],
  "client_better_areas": ["string"],
  "scores": {{
    "price_competitiveness": 0, "offer_competitiveness": 0,
    "menu_variety": 0, "delivery_strategy": 0,
    "customer_attraction": 0, "value_for_money": 0,
    "combo_effectiveness": 0, "sales_strategy": 0
  }},
  "recommendations": ["string"]
}}"""
        return self._ask(system, prompt, max_tokens=4096)

    def generate_pricing_recommendations(self, client_menu, market_data):
        """Generate AI pricing optimization recommendations."""
        system = "You are a restaurant pricing strategist. Return ONLY valid JSON."
        prompt = f"""Analyze pricing for this Indian restaurant and provide optimization recommendations.

CLIENT MENU: {json.dumps(client_menu, default=str)[:3000]}

MARKET DATA: {json.dumps(market_data, default=str)[:3000]}

Return JSON:
{{
  "reduce_price": [{{"item": "", "current": 0, "suggested": 0, "reason": ""}}],
  "increase_price": [{{"item": "", "current": 0, "suggested": 0, "reason": ""}}],
  "market_average": {{"category": "", "avg_price": 0}},
  "overpriced_alerts": [""],
  "underpriced_opportunities": [""],
  "summary": ""
}}"""
        return self._ask(system, prompt)

    def generate_sales_recommendations(self, client_data, competitor_data):
        """Generate AI sales optimization recommendations."""
        system = "You are a restaurant sales optimization expert. Return ONLY valid JSON."
        prompt = f"""Generate sales optimization strategies for this Indian restaurant.

CLIENT: {json.dumps(client_data, default=str)[:3000]}

COMPETITORS: {json.dumps(competitor_data, default=str)[:3000]}

Return JSON:
{{
  "offer_optimization": {{
    "combo_deals": [""], "lunch_specials": [""], "dinner_specials": [""],
    "family_packs": [""], "bogo_strategies": [""], "weekend_offers": [""],
    "festival_campaigns": [""], "student_offers": [""], "loyalty_programs": [""]
  }},
  "menu_optimization": {{
    "missing_dishes": [""], "trending_dishes": [""], "high_margin_dishes": [""],
    "premium_opportunities": [""], "healthier_options": [""]
  }},
  "sales_optimization": {{
    "upsell_opportunities": [""], "cross_sell_strategies": [""],
    "customer_retention": [""], "delivery_optimization": [""],
    "online_ordering": [""], "repeat_customer_campaigns": [""]
  }},
  "market_analysis": {{
    "cheapest_restaurant": "", "premium_restaurant": "",
    "best_rated": "", "most_discounted": "",
    "common_pricing_patterns": [""], "customer_trends": [""]
  }}
}}"""
        return self._ask(system, prompt)

    def find_website_for_restaurant(self, name, location="Leander, TX"):
        """Use Claude to dynamically find or guess the website link for a restaurant."""
        if not self.is_available():
            return None
        
        prompt = f"What is the official website URL for the restaurant '{name}' located in or near {location}? Return ONLY the raw URL string starting with http. If you don't know, return exactly 'None'."
        
        url = self._ask("You are a search assistant that strictly returns only what is asked.", prompt)
        
        if url and url.strip() != 'None' and url.startswith('http'):
            return url.strip()
        return None

claude_service = ClaudeService()
