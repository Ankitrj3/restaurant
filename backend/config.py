"""
Configuration management for the Restaurant Competitor Intelligence Platform.
Loads environment variables and provides typed config access.
"""

import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))


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
        if not cls.GRAPHHOPPER_API_KEY:
            warnings.append("GRAPHHOPPER_API_KEY is not set — distance calculations will use estimates")
        return warnings
