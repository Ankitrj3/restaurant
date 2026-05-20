import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import json
import gzip
import os
import time
from config import Config

class DatabaseService:
    def __init__(self):
        self.connection_pool = None
        self._init_pool()
        
    def _init_pool(self):
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                dsn=Config.DATABASE_URL
            )
            print("[Database] PostgreSQL connection pool initialized")
        except Exception as e:
            print(f"[Database] Failed to initialize connection pool: {e}")
            
    def get_connection(self):
        if self.connection_pool:
            try:
                return self.connection_pool.getconn()
            except Exception as e:
                print(f"[Database] Error getting connection from pool: {e}")
        return None

    def release_connection(self, conn):
        if self.connection_pool and conn:
            try:
                self.connection_pool.putconn(conn)
            except Exception as e:
                print(f"[Database] Error releasing connection: {e}")

    def execute_query(self, query, params=None, fetch=False):
        """Execute a query and optionally fetch results."""
        conn = self.get_connection()
        if not conn:
            return None if fetch else False

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch:
                    results = cursor.fetchall()
                    conn.commit()
                    return [dict(row) for row in results]
                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            print(f"[Database] Query execution error: {e}")
            return None if fetch else False
        finally:
            self.release_connection(conn)

    def execute_scalar(self, query, params=None):
        """Execute a query and fetch a single scalar value."""
        conn = self.get_connection()
        if not conn:
            return None
            
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                conn.commit()
                return result[0] if result else None
        except Exception as e:
            conn.rollback()
            print(f"[Database] Scalar query error: {e}")
            return None
        finally:
            self.release_connection(conn)

    # ── Database Snapshot Archival ──
    def archive_snapshot(self, snapshot_type, identifier, payload):
        """
        Store compressed DB snapshots (HTML, raw responses, etc.)
        snapshot_type: 'gemini', 'claude', 'html', 'comparison', 'menu'
        """
        try:
            # Compress the payload payload to save DB space
            json_payload = json.dumps(payload)
            compressed_data = gzip.compress(json_payload.encode('utf-8'))
            
            # Use raw_data in restaurants table or a dedicated snapshots table.
            # We will use the file system for actual JSON snapshots as per design,
            # but this method could store large binary blobs if a DB table exists.
            # Currently relying on the backend/cache JSON structure.
            pass
        except Exception as e:
            print(f"[Database] Error archiving snapshot: {e}")

database_service = DatabaseService()
