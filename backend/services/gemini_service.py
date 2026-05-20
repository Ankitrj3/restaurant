import json
import time
import requests
import urllib3
from config import Config

# Disable SSL warnings since we are using verify=False to bypass corporate proxy
urllib3.disable_warnings()

class GeminiService:
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        # Use gemini-2.0-flash for higher rate limits (2.5-flash is a thinking model with lower RPM)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        self._response_cache = {}
        # Circuit breaker: skip API calls for COOLDOWN seconds after a 429
        self._rate_limited_until = 0
        self._COOLDOWN_SECONDS = 300  # 5 minutes
    
    def is_available(self):
        if not self.api_key:
            return False
        # Circuit breaker: if recently rate-limited, report as unavailable
        if time.time() < self._rate_limited_until:
            return False
        return True
    
    def _trip_circuit_breaker(self):
        """Mark the API as rate-limited for the cooldown period."""
        self._rate_limited_until = time.time() + self._COOLDOWN_SECONDS
        print(f"[Gemini] Circuit breaker tripped — skipping API calls for {self._COOLDOWN_SECONDS}s")
    
    def _ask(self, system_prompt, user_prompt, max_tokens=8192, temperature=0.1):
        if not self.is_available():
            print("[Gemini] API key missing")
            return None
        
        # Cache check — deduplicate identical requests
        cache_key = hash(system_prompt + user_prompt)
        if cache_key in self._response_cache:
            return self._response_cache[cache_key]
        
        url = f"{self.base_url}?key={self.api_key}"
        
        # Combine system and user prompt since Gemini REST API handles them in contents
        full_prompt = f"System Instructions: {system_prompt}\n\nUser Request: {user_prompt}"
        
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json"
            }
        }
        
        try:
            resp = requests.post(
                url, 
                json=payload, 
                headers={'Content-Type': 'application/json'},
                verify=False,
                timeout=30
            )
            
            if resp.status_code == 429:
                print("[Gemini] Rate limited (429)")
                self._trip_circuit_breaker()
                return None
                
            resp.raise_for_status()
            data = resp.json()
            
            # Extract text from Gemini response
            if "candidates" in data and len(data["candidates"]) > 0:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                # Clean markdown
                text = text.replace("```json", "").replace("```", "").strip()
                try:
                    result = json.loads(text)
                    # Cache the successful response
                    self._response_cache[cache_key] = result
                    return result
                except json.JSONDecodeError:
                    print("[Gemini] Failed to parse JSON response:", text[:200])
                    return None
            return None
            
        except Exception as e:
            if '429' in str(e):
                self._trip_circuit_breaker()
            else:
                print(f"[Gemini] API error: {e}")
            return None

    def search_nearby_restaurants(self, location, radius_miles):
        """Use Gemini to dynamically discover nearby Indian restaurants."""
        system = (
            "You are a local business search API. Return ONLY a raw JSON array of objects. "
            "Do not use markdown blocks. Each object must represent a real, currently operating restaurant."
        )
        prompt = f"""
Find at least 10 real Indian, Pakistani, Nepalese, or Bengali restaurants within a {radius_miles} mile radius of {location}.
If {location} is a specific coordinate or address, center the search there.

Return EXACTLY this JSON structure, replacing the values with real data:
[
  {{
    "name": "Restaurant Name",
    "address": "Full Physical Address including city and state",
    "phone": "Phone number if known, otherwise N/A",
    "website_url": "Official website URL, or null if unknown",
    "latitude": 30.1234,
    "longitude": -97.1234,
    "cuisine_tags": ["Indian", "North Indian"]
  }}
]
Ensure latitude and longitude are floats.
"""
        return self._ask(system, prompt)
        
    def infer_restaurant_website(self, restaurant_name, restaurant_address):
        """Ask Gemini to infer the official website URL from name/address."""
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

    def extract_menu_from_text(self, text, restaurant_name):
        """Extract structured menu items from raw scraped text."""
        system = (
            "You are a highly accurate data extraction API. "
            "You will receive raw website text. Extract all menu items, prices, and categories into valid JSON. "
            "Return ONLY JSON, no markdown formatting."
        )
        prompt = f"""
Extract the menu for {restaurant_name} from the following text.

Rules:
1. Ignore navigational links, headers, footers.
2. Group items into logical categories (Appetizers, Biryani, Curries, Breads, Desserts, etc.).
3. Clean up the names and descriptions.
4. Extract the price as a float (e.g. 14.99). If no price, skip the item.
5. Guess 'is_veg' based on ingredients (paneer, vegetable, dal = true; chicken, lamb, beef = false).

Return JSON format:
{{
  "items": [
    {{
      "item_name": "Chicken Tikka Masala",
      "category": "Curries",
      "price": 15.99,
      "description": "Roasted chicken in creamy tomato sauce",
      "is_veg": false
    }}
  ]
}}

Raw text to analyze:
{text[:15000]}
"""
        return self._ask(system, prompt, max_tokens=4096)

    def extract_offers_from_text(self, text, restaurant_name):
        """Extract promotional offers from raw text."""
        system = (
            "You are a promotional offer extraction API. Extract any deals, discounts, or loyalty programs from the text. "
            "Return ONLY valid JSON."
        )
        prompt = f"""
Extract any special offers for {restaurant_name}.

Return JSON format:
{{
  "offers": [
    {{
      "title": "10% Off First Order",
      "description": "Get 10% off when you order online",
      "offer_type": "discount",
      "discount_percent": 10
    }}
  ]
}}

Raw text:
{text[:10000]}
"""
        return self._ask(system, prompt, max_tokens=2048)

    def compare_restaurants(self, client_data, competitor_data):
        """Generate a detailed one-to-one comparison between client and competitor."""
        system = (
            "You are a restaurant business intelligence analyst. "
            "Provide detailed, actionable comparison analysis. Return ONLY valid JSON."
        )
        prompt = f"""Compare these two Indian restaurants:

CLIENT
Name: {client_data.get('name')}
Menu: {json.dumps(client_data.get('menu', [])[:20])}

COMPETITOR
Name: {competitor_data.get('name')}
Menu: {json.dumps(competitor_data.get('menu', [])[:20])}

Return JSON format:
{{
  "price_comparison": "Client is 10% cheaper on average...",
  "menu_overlap": ["Chicken Biryani", "Butter Chicken"],
  "competitor_unique_items": ["Goat Haleem"],
  "strategic_recommendations": ["Add a lunch special to compete with their buffet."]
}}
"""
        return self._ask(system, prompt, max_tokens=2048)

gemini_service = GeminiService()
