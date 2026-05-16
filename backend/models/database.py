"""
Database access layer for PostgreSQL.
Provides connection pooling and CRUD operations for all entities.
"""

import json
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from config import Config


class Database:
    """PostgreSQL database manager with connection pooling."""

    def __init__(self):
        self.conn_params = {
            'host': Config.DB_HOST,
            'port': Config.DB_PORT,
            'dbname': Config.DB_NAME,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
        }
        self._conn = None

    def get_connection(self):
        """Get or create a database connection."""
        try:
            if self._conn is None or self._conn.closed:
                self._conn = psycopg2.connect(**self.conn_params)
                self._conn.autocommit = False
            return self._conn
        except psycopg2.OperationalError:
            # Database not available — return None for graceful degradation
            return None

    @contextmanager
    def cursor(self):
        """Context manager for database cursor with auto-commit/rollback."""
        conn = self.get_connection()
        if conn is None:
            yield None
            return
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def is_available(self):
        """Check if database is available."""
        try:
            conn = self.get_connection()
            if conn is None:
                return False
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return True
        except Exception:
            return False

    # --------------------------------------------------
    # Restaurant CRUD
    # --------------------------------------------------
    def save_restaurant(self, restaurant_data):
        """Insert or update a restaurant record."""
        with self.cursor() as cur:
            if cur is None:
                return None
            cur.execute("""
                INSERT INTO restaurants (
                    name, address, latitude, longitude, distance_miles,
                    rating, total_reviews, price_category, phone, website,
                    is_client, delivery_available, opening_hours,
                    delivery_platforms, cuisine_tags, image_url, source,
                    radius_group, raw_data
                ) VALUES (
                    %(name)s, %(address)s, %(latitude)s, %(longitude)s, %(distance_miles)s,
                    %(rating)s, %(total_reviews)s, %(price_category)s, %(phone)s, %(website)s,
                    %(is_client)s, %(delivery_available)s, %(opening_hours)s,
                    %(delivery_platforms)s, %(cuisine_tags)s, %(image_url)s, %(source)s,
                    %(radius_group)s, %(raw_data)s
                )
                ON CONFLICT DO NOTHING
                RETURNING id
            """, restaurant_data)
            result = cur.fetchone()
            return result['id'] if result else None

    def get_all_restaurants(self, exclude_client=False):
        """Get all restaurants, optionally excluding the client."""
        with self.cursor() as cur:
            if cur is None:
                return []
            query = "SELECT * FROM restaurants"
            if exclude_client:
                query += " WHERE is_client = FALSE"
            query += " ORDER BY distance_miles ASC"
            cur.execute(query)
            return [dict(row) for row in cur.fetchall()]

    def get_restaurant(self, restaurant_id):
        """Get a single restaurant by ID."""
        with self.cursor() as cur:
            if cur is None:
                return None
            cur.execute("SELECT * FROM restaurants WHERE id = %s", (restaurant_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_client_restaurant(self):
        """Get the client restaurant record."""
        with self.cursor() as cur:
            if cur is None:
                return None
            cur.execute("SELECT * FROM restaurants WHERE is_client = TRUE LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None

    # --------------------------------------------------
    # Menu Items CRUD
    # --------------------------------------------------
    def save_menu_items(self, restaurant_id, items):
        """Bulk-insert menu items for a restaurant."""
        with self.cursor() as cur:
            if cur is None:
                return
            # Clear existing items first
            cur.execute("DELETE FROM menu_items WHERE restaurant_id = %s", (restaurant_id,))
            for item in items:
                item['restaurant_id'] = restaurant_id
                cur.execute("""
                    INSERT INTO menu_items (
                        restaurant_id, item_name, category, description, price,
                        is_veg, is_popular, is_signature, is_bestseller,
                        spice_level, image_url, source
                    ) VALUES (
                        %(restaurant_id)s, %(item_name)s, %(category)s, %(description)s, %(price)s,
                        %(is_veg)s, %(is_popular)s, %(is_signature)s, %(is_bestseller)s,
                        %(spice_level)s, %(image_url)s, %(source)s
                    )
                """, item)

    def get_menu_items(self, restaurant_id):
        """Get all menu items for a restaurant."""
        with self.cursor() as cur:
            if cur is None:
                return []
            cur.execute(
                "SELECT * FROM menu_items WHERE restaurant_id = %s ORDER BY category, item_name",
                (restaurant_id,)
            )
            return [dict(row) for row in cur.fetchall()]

    # --------------------------------------------------
    # Offers CRUD
    # --------------------------------------------------
    def save_offers(self, restaurant_id, offers):
        """Bulk-insert offers for a restaurant."""
        with self.cursor() as cur:
            if cur is None:
                return
            cur.execute("DELETE FROM offers WHERE restaurant_id = %s", (restaurant_id,))
            for offer in offers:
                offer['restaurant_id'] = restaurant_id
                cur.execute("""
                    INSERT INTO offers (
                        restaurant_id, offer_type, title, description,
                        discount_percent, discount_amount, min_order_amount,
                        code, platform, is_active, source
                    ) VALUES (
                        %(restaurant_id)s, %(offer_type)s, %(title)s, %(description)s,
                        %(discount_percent)s, %(discount_amount)s, %(min_order_amount)s,
                        %(code)s, %(platform)s, %(is_active)s, %(source)s
                    )
                """, offer)

    def get_offers(self, restaurant_id):
        """Get active offers for a restaurant."""
        with self.cursor() as cur:
            if cur is None:
                return []
            cur.execute(
                "SELECT * FROM offers WHERE restaurant_id = %s AND is_active = TRUE",
                (restaurant_id,)
            )
            return [dict(row) for row in cur.fetchall()]

    # --------------------------------------------------
    # Comparison CRUD
    # --------------------------------------------------
    def save_comparison(self, comparison_data):
        """Save a comparison result."""
        with self.cursor() as cur:
            if cur is None:
                return None
            cur.execute("""
                INSERT INTO comparisons (
                    competitor_id, client_id, price_comparison, offer_comparison,
                    menu_comparison, customer_attraction, competitor_better_areas,
                    client_better_areas, recommendations, scores
                ) VALUES (
                    %(competitor_id)s, %(client_id)s, %(price_comparison)s, %(offer_comparison)s,
                    %(menu_comparison)s, %(customer_attraction)s, %(competitor_better_areas)s,
                    %(client_better_areas)s, %(recommendations)s, %(scores)s
                )
                RETURNING id
            """, comparison_data)
            result = cur.fetchone()
            return result['id'] if result else None

    def close(self):
        """Close the database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()


# Singleton instance
db = Database()
