"""
Configuration management for the Restaurant Competitor Intelligence Platform.
Loads environment variables and provides typed config access.
"""

import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'), override=True)


class Config:
    """Application configuration loaded from environment variables."""

    # --- Flask ---
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))

    # --- API Keys ---
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    GRAPHHOPPER_API_KEY = os.getenv('GRAPHHOPPER_API_KEY', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

    # --- PostgreSQL ---
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:password@localhost:5432/restaurant_intel'
    )
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'restaurant_intel')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')

    # --- Client Restaurant ---
    CLIENT_RESTAURANT_NAME = os.getenv('CLIENT_RESTAURANT_NAME', 'Bawarchi Biryanis')
    CLIENT_RESTAURANT_ADDRESS = os.getenv(
        'CLIENT_RESTAURANT_ADDRESS',
        '1611 S College Ave #100, Fort Collins, CO 80525, United States'
    )
    CLIENT_LAT = float(os.getenv('CLIENT_LAT', 40.5653))
    CLIENT_LNG = float(os.getenv('CLIENT_LNG', -105.0844))
    CLIENT_MENU_URL = os.getenv('CLIENT_MENU_URL', 'https://www.bawarchibiryanis.com/menu')
    CLIENT_MENU_CACHE_SECONDS = int(os.getenv('CLIENT_MENU_CACHE_SECONDS', 21600))
    COMPETITOR_MENU_CACHE_SECONDS = int(os.getenv('COMPETITOR_MENU_CACHE_SECONDS', 21600))
    COMPETITOR_OFFERS_CACHE_SECONDS = int(os.getenv('COMPETITOR_OFFERS_CACHE_SECONDS', 21600))
    COMPETITOR_WEBSITE_GUESS_ENABLED = os.getenv('COMPETITOR_WEBSITE_GUESS_ENABLED', '1') == '1'

    # --- Platform Adapters ---
    UBEREATS_SCRAPE_ENABLED = os.getenv('UBEREATS_SCRAPE_ENABLED', '1') == '1'
    DOORDASH_SCRAPE_ENABLED = os.getenv('DOORDASH_SCRAPE_ENABLED', '1') == '1'
    GRUBHUB_SCRAPE_ENABLED = os.getenv('GRUBHUB_SCRAPE_ENABLED', '1') == '1'
    PLATFORM_CACHE_TTL = int(os.getenv('PLATFORM_CACHE_TTL', 3600))
    SCRAPING_FALLBACK_ENABLED = os.getenv('SCRAPING_FALLBACK_ENABLED', '1') == '1'

    # --- Fuzzy Matching ---
    FUZZY_MATCH_THRESHOLD = float(os.getenv('FUZZY_MATCH_THRESHOLD', '0.65'))

    # --- Search Configuration ---
    SEARCH_RADII_MILES = [3, 5, 10, 15, 20]
    MIN_COMPETITORS = int(os.getenv('MIN_COMPETITORS', 5))

    # --- Scraping ---
    REQUEST_TIMEOUT = 30
    USER_AGENT = (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    )

    @classmethod
    def validate(cls):
        """Validate that critical configuration is present."""
        warnings = []
        if not cls.ANTHROPIC_API_KEY:
            warnings.append("ANTHROPIC_API_KEY is not set — AI features will use mock data")
        if not cls.GEMINI_API_KEY:
            warnings.append("GEMINI_API_KEY is not set — AI features will use mock data")
        
        if not cls.GRAPHHOPPER_API_KEY:
            warnings.append("GRAPHHOPPER_API_KEY is not set — distance calculations will use estimates")
        return warnings
