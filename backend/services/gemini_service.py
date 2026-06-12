"""
Gemini Service — Google AI integration with Search Grounding.
Uses google_search tool to fetch REAL-TIME data from the web,
including restaurant menus, delivery platform prices, and competitor info.
"""

import json
import re
import time
import requests
import urllib3
from config import Config

# Disable SSL warnings since we are using verify=False to bypass corporate proxy
urllib3.disable_warnings()

# ── Global source registry ─────────────────────────────────────────────────
# Stores the real web URLs that Gemini used for each grounded call type.
# Shape: { call_label: [ {"url": ..., "title": ..., "call": ...}, ... ] }
_source_registry = {}


def get_source_registry():
    """Return a copy of the accumulated source registry (all grounding URLs seen)."""
    return dict(_source_registry)


def _register_sources(label, sources):
    """Add sources to the registry under the given label."""
    if label not in _source_registry:
        _source_registry[label] = []
    for s in sources:
        # Avoid exact duplicates
        if s not in _source_registry[label]:
            _source_registry[label].append(s)


class GeminiService:
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        self._response_cache = {}
        # Circuit breaker: skip API calls for COOLDOWN seconds after a 429
        self._rate_limited_until: float = 0.0
        self._COOLDOWN_SECONDS = 60  # retry after 60s (free tier resets per-minute)

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

    def _extract_json_from_text(self, text):
        """Extract JSON object or array from a text response that may contain markdown or prose."""
        if not text:
            return None
        # Strip markdown code fences
        cleaned = text.replace("```json", "").replace("```", "").strip()
        # Try parsing the whole cleaned text as JSON
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        # Try to find a JSON object {...} in the text
        obj_match = re.search(r'\{[\s\S]*\}', cleaned)
        if obj_match:
            try:
                return json.loads(obj_match.group())
            except json.JSONDecodeError:
                pass
        # Try to find a JSON array [...] in the text
        arr_match = re.search(r'\[[\s\S]*\]', cleaned)
        if arr_match:
            try:
                return json.loads(arr_match.group())
            except json.JSONDecodeError:
                pass
        return None

    def _ask(self, system_prompt, user_prompt, max_tokens=8192, temperature=0.1):
        """Non-grounded call — uses responseMimeType for structured JSON output.
        Use this for data transformation/analysis where web search is not needed."""
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
                timeout=60
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
                result = self._extract_json_from_text(text)
                if result is not None:
                    self._response_cache[cache_key] = result
                    return result
                else:
                    print("[Gemini] Failed to parse JSON response:", text[:300])
                    return None
            return None

        except Exception as e:
            if '429' in str(e):
                self._trip_circuit_breaker()
            else:
                print(f"[Gemini] API error: {e}")
            return None

    def _ask_grounded(self, system_prompt, user_prompt, max_tokens=8192, temperature=0.2):
        """Grounded call — enables Google Search tool so Gemini searches the web
        for REAL-TIME data (restaurant listings, menu prices, delivery platform info).

        IMPORTANT: responseMimeType='application/json' is INCOMPATIBLE with grounding tools.
        So we request JSON in the prompt and parse it from the text response.
        """
        if not self.is_available():
            print("[Gemini] API key missing")
            return None

        # Cache check
        cache_key = hash("grounded_" + system_prompt + user_prompt)
        if cache_key in self._response_cache:
            return self._response_cache[cache_key]

        url = f"{self.base_url}?key={self.api_key}"

        full_prompt = f"System Instructions: {system_prompt}\n\nUser Request: {user_prompt}"

        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "tools": [
                {"google_search": {}}
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
                # NO responseMimeType here — incompatible with google_search tool
            }
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                verify=False,
                timeout=90  # Grounded calls take longer (web search + generation)
            )

            if resp.status_code == 429:
                print("[Gemini] Rate limited (429) on grounded call")
                self._trip_circuit_breaker()
                return None

            if resp.status_code != 200:
                print(f"[Gemini] Grounded call failed: {resp.status_code} — {resp.text[:500]}")
                resp.raise_for_status()

            data = resp.json()

            # Extract text from grounded response
            if "candidates" in data and len(data["candidates"]) > 0:
                parts = data["candidates"][0]["content"]["parts"]
                # Grounded responses may have multiple parts — concatenate text parts
                text_parts = [p["text"] for p in parts if "text" in p]
                full_text = "\n".join(text_parts)

                # ── Parse grounding metadata (real web URLs Gemini searched) ──
                grounding = data["candidates"][0].get("groundingMetadata", {})
                web_chunks = grounding.get("groundingChunks", [])
                search_queries_used = [
                    q.get("query", "")
                    for q in grounding.get("webSearchQueries", [])
                    if q.get("query")
                ]

                # Build a clean list of source objects
                parsed_sources = []
                for chunk in web_chunks:
                    web = chunk.get("web", {})
                    uri = web.get("uri") or web.get("url")
                    title = web.get("title", "")
                    if uri:
                        parsed_sources.append({
                            "url": uri,
                            "title": title,
                            "search_queries": search_queries_used,
                        })

                if parsed_sources:
                    print(f"[Gemini] Grounded with {len(parsed_sources)} web sources: "
                          f"{[s['url'] for s in parsed_sources[:3]]}")
                    # Store in module-level registry keyed by prompt fingerprint
                    label = user_prompt[:80].strip().replace('\n', ' ')
                    _register_sources(label, parsed_sources)

                result = self._extract_json_from_text(full_text)
                if result is not None:
                    # Attach source URLs directly onto the result so callers can surface them
                    if isinstance(result, dict):
                        result['_sources'] = parsed_sources
                        result['_search_queries'] = search_queries_used
                    elif isinstance(result, list) and parsed_sources:
                        # For list results, wrap in a dict so sources are still accessible
                        # but keep backward compatibility — attach on first element metadata
                        pass  # List callers should check get_source_registry()
                    self._response_cache[cache_key] = result
                    return result
                else:
                    print(f"[Gemini] Grounded response had no parseable JSON. Raw text: {full_text[:500]}")
                    return None
            return None

        except Exception as e:
            if '429' in str(e):
                self._trip_circuit_breaker()
            else:
                print(f"[Gemini] Grounded API error: {e}")
            return None

    # ── Public Methods (all use grounded search for real data) ──────────

    def search_nearby_restaurants(self, location, radius_miles, address=None):
        """Use Gemini with Google Search to discover REAL nearby Indian restaurants."""
        if not address:
            address = Config.CLIENT_RESTAURANT_ADDRESS

        # Parse street/city/state from address for local query terms
        parts = [p.strip() for p in address.split(',') if p.strip()]
        city_state = ""
        if len(parts) >= 3:
            city_state = f"{parts[-3]} {parts[-2].split()[0]}" # E.g. "Leander TX"
        else:
            city_state = address

        system = (
            "You are a local business data extraction agent with Google Search access. "
            "Search Google Maps and the web for REAL, currently operating restaurants. "
            "Return ONLY a raw JSON array. Do not include any explanation or markdown."
        )
        prompt = f"""Search for real Indian, Pakistani, Nepalese, or Bengali restaurants 
within a {radius_miles}-mile radius of coordinates {location} (located at {address}).

Use Google Search to find REAL restaurants that are currently open and operating in this specific local area.
You MUST search using local query terms targeting {city_state} or the surrounding area to avoid returning search results from other locations or countries.

Return EXACTLY this JSON array format:
[
  {{
    "name": "Actual Restaurant Name",
    "address": "Full Real Street Address, City, State ZIP",
    "phone": "Real phone number or N/A",
    "website_url": "Real website URL or null",
    "latitude": 30.1234,
    "longitude": -97.1234,
    "cuisine_tags": ["Indian", "South Indian"]
  }}
]

IMPORTANT: Only include REAL restaurants you can verify exist. Do NOT make up restaurants.
Ensure latitude and longitude are accurate floats for the actual location.
"""
        return self._ask_grounded(system, prompt, max_tokens=4096)

    def infer_restaurant_website(self, restaurant_name, restaurant_address):
        """Use grounded search to find the actual website URL for a restaurant."""
        system = (
            "You are a search assistant with Google Search access. "
            "Find the real official website for this restaurant. Return ONLY valid JSON."
        )
        prompt = f"""Search Google for the official website of this restaurant:

Restaurant: {restaurant_name}
Address: {restaurant_address}

Return JSON:
{{
  "website_url": "https://actual-website.com" or null if not found
}}
"""
        return self._ask_grounded(system, prompt, max_tokens=512)

    def extract_menu_from_text(self, text, restaurant_name):
        """Extract structured menu items from raw scraped text.
        This is a data transformation task — no web search needed."""
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
        """Extract promotional offers from raw text.
        Data transformation — no web search needed."""
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

    def fetch_restaurant_menu_from_platform(self, restaurant_name, restaurant_address, platform):
        """Use Google Search grounding to find REAL menu prices from a delivery platform.
        
        This is the KEY method that searches UberEats/DoorDash/Grubhub for actual prices.
        """
        platform_sites = {
            'ubereats': 'ubereats.com',
            'doordash': 'doordash.com',
            'grubhub': 'grubhub.com',
            'instore': 'the restaurant official website or Google Maps',
        }
        site = platform_sites.get(platform, 'Google')

        system = (
            "You are a restaurant menu price extraction agent with Google Search access. "
            "Search the web for REAL menu prices. Return ONLY a JSON object. "
            "Do NOT guess or estimate — only return prices you can actually find from search results."
        )
        prompt = f"""Search {site} for the menu and prices of "{restaurant_name}" located at {restaurant_address}.

Search queries to try:
- "{restaurant_name} {platform} menu prices"
- "{restaurant_name} {restaurant_address} menu"  
- site:{site} "{restaurant_name}"

Extract ALL menu items with their REAL prices as listed on {platform}.

Return this exact JSON format:
{{
  "restaurant_name": "{restaurant_name}",
  "platform": "{platform}",
  "platform_url": "the direct URL to this restaurant's page on {site} (e.g. https://www.{site}/store/...)",
  "data_source": "google_search_grounding",
  "items": [
    {{
      "item_name": "Chicken Biryani",
      "category": "Biryani",
      "price": 16.99,
      "is_veg": false,
      "description": "Aromatic basmati rice with chicken",
      "is_available": true
    }}
  ]
}}

IMPORTANT: 
- Return REAL prices from search results, not estimates.
- Include the REAL direct URL to the restaurant's page on {site} as "platform_url". This is critical.
- If you cannot find this restaurant on {platform}, return {{"items": [], "not_found": true}}
- Include at least the main menu categories: Biryani, Curries, Starters/Appetizers, Tandoori, Desserts.
"""
        return self._ask_grounded(system, prompt, max_tokens=8192)

    def fetch_delivery_fees_from_platform(self, restaurant_name, platform, restaurant_address=None):
        """Use Google Search grounding to find REAL delivery fees from a platform."""
        if not restaurant_address:
            restaurant_address = Config.CLIENT_RESTAURANT_ADDRESS

        system = (
            "You are a delivery logistics data agent with Google Search access. "
            "Search for real delivery fee information. Return ONLY valid JSON."
        )
        prompt = f"""Search for delivery fees for "{restaurant_name}" on {platform}.

Search for:
- "{restaurant_name} {platform} delivery fee"
- "{platform} delivery fee near {restaurant_address}"

Return JSON:
{{
  "delivery_fee": 3.99,
  "service_fee": 2.99,
  "surge_fee": 0,
  "tax_estimate": 2.50,
  "free_delivery_threshold": 25.00,
  "min_order_amount": 12.00,
  "estimated_delivery_time": "30-45 min",
  "has_free_delivery_over_15_promo": false,
  "data_source": "google_search_grounding"
}}

If you cannot find exact fees, return your best estimate based on typical {platform} fees in the {restaurant_address} area and mark data_source as "estimated".
"""
        return self._ask_grounded(system, prompt, max_tokens=1024)

    def fetch_full_market_data(self, lat, lng, radius_miles, restaurant_name, restaurant_address):
        """Single comprehensive grounded call to fetch the full market matrix.
        
        This is an optimized method that gets competitor data + pricing in one call
        to minimize API calls and avoid rate limiting.
        """
        system = (
            "You are a restaurant market intelligence agent with Google Search access. "
            "Search the web for REAL restaurant data. Your job is to find actual Indian restaurants "
            "near the given location and their real menu prices across platforms. "
            "Return ONLY a JSON object — no explanation text."
        )

        # Parse street/city/state from restaurant_address for local query terms
        parts = [p.strip() for p in restaurant_address.split(',') if p.strip()]
        city_state = ""
        street_area = ""
        if len(parts) >= 3:
            city_state = f"{parts[-3]} {parts[-2].split()[0]}" # E.g. "Leander TX"
            street_area = parts[0]
        else:
            city_state = restaurant_address

        query_terms = [
            f"Indian restaurants near {restaurant_address}",
            f"Indian restaurants near {restaurant_name}"
        ]
        if city_state:
            query_terms.append(f"Indian restaurants {city_state}")
            query_terms.append(f"restaurants {city_state}")
        if street_area:
            query_terms.append(f"Indian food near {street_area}")

        step1_queries = "\n".join([f'- "{q}"' for q in query_terms])

        prompt = f"""Search Google for Indian cuisine restaurants within {radius_miles} miles of:
Coordinates: {lat}, {lng}  
Address: {restaurant_address}

STEP 1: Find all Indian restaurants near this location. Search for:
{step1_queries}

STEP 2: For EACH restaurant found (including "{restaurant_name}"), search for their menu prices:
- Search their official website menu
- Search "{restaurant_name}" on UberEats, DoorDash, Grubhub
- Extract REAL prices from search results

STEP 3: Return this JSON:
{{
  "target_restaurant": {{
    "name": "{restaurant_name}",
    "address": "{restaurant_address}",
    "instore_menu": [
      {{"item_name": "Dish Name", "category": "Biryani|Curries|Starter|Tandoori|Dessert", "price": 16.99, "is_veg": false}}
    ],
    "ubereats_menu": [...],
    "doordash_menu": [...],
    "grubhub_menu": [...]
  }},
  "competitors": [
    {{
      "name": "Competitor Name",
      "address": "Full Address",
      "latitude": 30.123,
      "longitude": -97.456,
      "cuisine_tags": ["Indian"],
      "instore_menu": [...],
      "ubereats_menu": [...],
      "doordash_menu": [...],
      "grubhub_menu": [...]
    }}
  ],
  "delivery_fees": [
    {{
      "restaurant_name": "Name",
      "uber_delivery_fee": 3.99,
      "doordash_delivery_fee": 2.99,
      "grubhub_delivery_fee": 3.49,
      "has_free_delivery_over_15_promo": true
    }}
  ]
}}

CRITICAL RULES:
- Use REAL data from Google Search results only
- Include ALL Indian restaurants you can find within {radius_miles} miles
- If a restaurant is not on a platform, set that platform menu to empty array []
- Prices must be real USD floats (e.g., 16.99)
- Categories MUST be one of: Biryani, Curries, Starter, Tandoori, Dessert (or other descriptive category)
"""
        return self._ask_grounded(system, prompt, max_tokens=16384, temperature=0.1)

    def search_restaurant_platform_url(self, restaurant_name, restaurant_address, platform):
        """Use Google Search grounding to find the REAL URL for a restaurant on a delivery platform.
        
        Lightweight grounded call — returns just the URL, not menu data.
        The search is explicitly anchored to the configured restaurant address (US location)
        to prevent geo-IP bias from returning results from the wrong country/region.
        """
        if not self.is_available():
            return None

        platform_domains = {
            'ubereats': 'ubereats.com',
            'doordash': 'doordash.com',
            'grubhub': 'grubhub.com',
        }
        domain = platform_domains.get(platform)
        if not domain:
            return None

        platform_labels = {
            'ubereats': 'Uber Eats',
            'doordash': 'DoorDash',
            'grubhub': 'Grubhub',
        }
        label = platform_labels.get(platform, platform)

        # Parse city/state from address for extra location anchoring
        parts = [p.strip() for p in restaurant_address.split(',') if p.strip()]
        city_state = ""
        zip_code = ""
        if len(parts) >= 3:
            city_state = f"{parts[-3]} {parts[-2].split()[0]}"  # e.g. "Leander TX"
            # Try to extract ZIP from the state field (e.g. "TX 78641")
            state_parts = parts[-2].split()
            if len(state_parts) >= 2:
                zip_code = state_parts[-1]
        else:
            city_state = restaurant_address

        system = (
            "You are a URL lookup agent with Google Search access. "
            "Find the exact URL for a restaurant on a US food delivery platform. "
            "The restaurant is located in the United States. "
            "Return ONLY valid JSON."
        )
        prompt = f"""Find the real {label} page URL for this restaurant located in the UNITED STATES:

Restaurant: {restaurant_name}
Full Address: {restaurant_address}
City/State: {city_state}
Country: United States

IMPORTANT LOCATION CONTEXT: This restaurant is located in {city_state}, United States.
You MUST search for the US listing. Do NOT return results from India, UK, Canada, or any other country.

Search queries to try (in order of priority):
1. site:{domain} "{restaurant_name}" "{city_state}"
2. "{restaurant_name}" {label} {city_state} Texas United States
3. "{restaurant_name}" {restaurant_address} {label}
4. site:{domain} "{restaurant_name}"

Verify the URL matches the correct US location before returning it.

Return JSON:
{{
  "platform": "{platform}",
  "platform_url": "https://www.{domain}/store/restaurant-slug/..." or null if not found,
  "found": true or false,
  "location_verified": true or false
}}

CRITICAL: 
- Return the REAL direct URL to the US restaurant's page on {label}
- The URL must be for the restaurant at {city_state}, NOT for any restaurant in India or other countries
- Do NOT guess or fabricate a URL
- If you cannot find a verified US URL, return null for platform_url and false for found
"""
        return self._ask_grounded(system, prompt, max_tokens=512)


gemini_service = GeminiService()
