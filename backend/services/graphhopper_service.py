"""
GraphHopper API service for geocoding and distance calculations.
Handles nearby restaurant search and distance computation.
"""

import requests
import math
import time
from config import Config


class GraphHopperService:
    """Service for geocoding, routing, and distance calculations using GraphHopper API."""

    BASE_URL = "https://graphhopper.com/api/1"

    def __init__(self):
        self.api_key = Config.GRAPHHOPPER_API_KEY
        self.client_lat = Config.CLIENT_LAT
        self.client_lng = Config.CLIENT_LNG
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({'Accept': 'application/json'})

    def geocode(self, address):
        """
        Convert an address to lat/lng coordinates using GraphHopper Geocoding API.
        Returns: {'lat': float, 'lng': float, 'formatted': str} or None
        """
        if not self.api_key:
            return self._fallback_geocode(address)

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/geocode",
                params={
                    'q': address,
                    'locale': 'en',
                    'limit': 1,
                    'key': self.api_key,
                },
                timeout=Config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get('hits'):
                hit = data['hits'][0]
                return {
                    'lat': hit['point']['lat'],
                    'lng': hit['point']['lng'],
                    'formatted': hit.get('name', address),
                }
        except Exception as e:
            print(f"[GraphHopper] Geocoding error: {e}")

        return self._fallback_geocode(address)

    def calculate_distance(self, lat1, lng1, lat2, lng2):
        """
        Calculate driving distance between two points using GraphHopper Routing API.
        Returns distance in miles and duration in minutes.
        """
        if not self.api_key:
            return self._haversine_distance(lat1, lng1, lat2, lng2)

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/route",
                params={
                    'point': [f"{lat1},{lng1}", f"{lat2},{lng2}"],
                    'vehicle': 'car',
                    'locale': 'en',
                    'calc_points': 'false',
                    'key': self.api_key,
                },
                timeout=Config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get('paths'):
                path = data['paths'][0]
                distance_miles = path['distance'] / 1609.34  # meters to miles
                duration_minutes = path['time'] / 60000  # ms to minutes
                return {
                    'distance_miles': round(distance_miles, 2),
                    'duration_minutes': round(duration_minutes, 1),
                }
        except Exception as e:
            print(f"[GraphHopper] Routing error: {e}")

        return self._haversine_distance(lat1, lng1, lat2, lng2)

    def calculate_distance_from_client(self, lat, lng):
        """Calculate distance from the client restaurant to the given coordinates.
        Uses Haversine for batch operations to conserve API quota.
        """
        return self._haversine_distance(self.client_lat, self.client_lng, lat, lng)

    def is_within_radius(self, lat, lng, radius_miles):
        """Check if a point is within the given radius from the client restaurant."""
        result = self._haversine_distance(self.client_lat, self.client_lng, lat, lng)
        return result['distance_miles'] <= radius_miles

    def get_radius_group(self, distance_miles):
        """Determine which radius group a restaurant belongs to."""
        for radius in Config.SEARCH_RADII_MILES:
            if distance_miles <= radius:
                return f"{radius}mi"
        return f">{Config.SEARCH_RADII_MILES[-1]}mi"

    def search_nearby_places(self, query, radius_miles=10):
        """
        Search for nearby places using GraphHopper Geocoding API.
        Returns list of places within the radius.
        """
        if not self.api_key:
            return []

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/geocode",
                params={
                    'q': query,
                    'locale': 'en',
                    'limit': 50,
                    'point': f"{self.client_lat},{self.client_lng}",
                    'key': self.api_key,
                },
                timeout=Config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            places = []
            for hit in data.get('hits', []):
                lat = hit['point']['lat']
                lng = hit['point']['lng']
                dist = self._haversine_distance(self.client_lat, self.client_lng, lat, lng)

                if dist['distance_miles'] <= radius_miles:
                    places.append({
                        'name': hit.get('name', ''),
                        'address': self._format_address(hit),
                        'lat': lat,
                        'lng': lng,
                        'distance_miles': dist['distance_miles'],
                        'radius_group': self.get_radius_group(dist['distance_miles']),
                    })

            return sorted(places, key=lambda x: x['distance_miles'])

        except Exception as e:
            print(f"[GraphHopper] Search error: {e}")
            return []

    # --------------------------------------------------
    # Private / Fallback Methods
    # --------------------------------------------------

    def _haversine_distance(self, lat1, lng1, lat2, lng2):
        """Calculate straight-line distance using the Haversine formula."""
        R = 3958.8  # Earth's radius in miles

        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        distance = R * c
        # Rough estimate: driving distance ≈ 1.3× straight-line
        driving_distance = round(distance * 1.3, 2)
        duration = round(driving_distance * 2, 1)  # ~2 min per mile

        return {
            'distance_miles': round(distance, 2),
            'driving_distance_miles': driving_distance,
            'duration_minutes': duration,
        }

    def _fallback_geocode(self, address):
        """Fallback geocoding using Nominatim (no API key needed)."""
        try:
            resp = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={'q': address, 'format': 'json', 'limit': 1},
                headers={'User-Agent': Config.USER_AGENT},
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()
            if results:
                return {
                    'lat': float(results[0]['lat']),
                    'lng': float(results[0]['lon']),
                    'formatted': results[0].get('display_name', address),
                }
        except Exception as e:
            print(f"[Nominatim] Geocoding fallback error: {e}")
        return None

    def _format_address(self, hit):
        """Format a GraphHopper hit into a readable address."""
        parts = []
        for key in ['street', 'housenumber', 'city', 'state', 'postcode', 'country']:
            if hit.get(key):
                parts.append(str(hit[key]))
        return ', '.join(parts) if parts else hit.get('name', 'Unknown')


# Singleton instance
graphhopper_service = GraphHopperService()
