import os
import json
import time
import shutil
from pathlib import Path
from services.database_service import database_service

class CacheService:
    def __init__(self):
        self.base_cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache')
        self._memory_cache = {}
        self.MAX_CACHE_SIZE_BYTES = 1024 * 1024 * 1024 # 1GB
        
        # Specific TTLs from implementation plan (in seconds)
        self.TTLS = {
            'discovery': 24 * 3600,
            'menu': 6 * 3600,
            'delivery_fee': 30 * 60,
            'comparison': 3600,
            'ai_response': 12 * 3600,
            'route': 24 * 3600
        }
        
    def _get_file_path(self, category, key):
        """Get the JSON snapshot file path."""
        # Sanitize key for filesystem
        key_str = str(key)
        safe_key = "".join([c if c.isalnum() else "_" for c in key_str])
        dir_path = os.path.join(self.base_cache_dir, category)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, f"{safe_key}.json")

    def get(self, category, key):
        """Retrieve from Memory -> DB -> JSON Snapshot."""
        key_str = str(key)
        cache_key = f"{category}:{key_str}"
        ttl = self.TTLS.get(category, 3600)
        current_time = time.time()
        
        # 1. Check Memory Cache
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if current_time - entry['timestamp'] < ttl:
                # Add stale warning timestamp for frontend if it's getting old
                data = entry['data']
                if isinstance(data, dict):
                    data['_cached_at'] = entry['timestamp']
                return data
                
        # 2. Check Database (Comparison Cache Table)
        if category == 'comparison':
            query = "SELECT result_data, created_at, expires_at FROM comparison_cache WHERE params_hash = %s AND expires_at > NOW()"
            result = database_service.execute_query(query, (key,), fetch=True)
            if result and len(result) > 0:
                data = result[0]['result_data']
                data['_cached_at'] = result[0]['created_at'].timestamp() if hasattr(result[0]['created_at'], 'timestamp') else time.time()
                self._memory_cache[cache_key] = {'data': data, 'timestamp': data['_cached_at']}
                return data

        # 3. Check Local JSON Snapshot
        file_path = self._get_file_path(category, key)
        if os.path.exists(file_path):
            try:
                mtime = os.path.getmtime(file_path)
                if current_time - mtime < ttl:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            data['_cached_at'] = mtime
                        self._memory_cache[cache_key] = {'data': data, 'timestamp': mtime}
                        return data
            except Exception as e:
                print(f"[Cache] Error reading snapshot {file_path}: {e}")
                
    def get_latest(self, category, key):
        """Retrieve from Memory -> DB -> JSON Snapshot ignoring TTL (for offline fallback)."""
        key_str = str(key)
        cache_key = f"{category}:{key_str}"
        
        # 1. Check Memory Cache
        if cache_key in self._memory_cache:
            data = self._memory_cache[cache_key]['data']
            if isinstance(data, dict):
                data['_cached_at'] = self._memory_cache[cache_key]['timestamp']
            return data
                
        # 2. Check Database (Comparison Cache Table)
        if category == 'comparison':
            query = "SELECT result_data, created_at FROM comparison_cache WHERE params_hash = %s ORDER BY created_at DESC LIMIT 1"
            result = database_service.execute_query(query, (key,), fetch=True)
            if result and len(result) > 0:
                data = result[0]['result_data']
                data['_cached_at'] = result[0]['created_at'].timestamp() if hasattr(result[0]['created_at'], 'timestamp') else time.time()
                self._memory_cache[cache_key] = {'data': data, 'timestamp': data['_cached_at']}
                return data

        # 3. Check Local JSON Snapshot
        file_path = self._get_file_path(category, key)
        if os.path.exists(file_path):
            try:
                mtime = os.path.getmtime(file_path)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        data['_cached_at'] = mtime
                    self._memory_cache[cache_key] = {'data': data, 'timestamp': mtime}
                    return data
            except Exception as e:
                print(f"[Cache] Error reading snapshot {file_path}: {e}")
                
        return None

    def set(self, category, key, data):
        """Save to Memory -> DB -> JSON Snapshot."""
        key_str = str(key)
        cache_key = f"{category}:{key_str}"
        current_time = time.time()
        ttl = self.TTLS.get(category, 3600)
        
        # 1. Memory Cache
        self._memory_cache[cache_key] = {'data': data, 'timestamp': current_time}
        
        # 2. Database
        if category == 'comparison':
            query = """
            INSERT INTO comparison_cache (comparison_type, params_hash, result_data, created_at, expires_at)
            VALUES (%s, %s, %s, NOW(), NOW() + interval '%s seconds')
            ON CONFLICT (comparison_type, params_hash) 
            DO UPDATE SET result_data = EXCLUDED.result_data, created_at = NOW(), expires_at = EXCLUDED.expires_at
            """
            database_service.execute_query(query, (category, key, json.dumps(data), ttl))

        # 3. JSON Snapshot
        file_path = self._get_file_path(category, key)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[Cache] Error writing snapshot {file_path}: {e}")
            
        # Trigger cleanup if size exceeded
        self._enforce_size_limit()

    def _enforce_size_limit(self):
        """Enforce the 1GB rolling cache limit by deleting oldest files."""
        total_size = 0
        files_with_stats = []
        
        for root, _, files in os.walk(self.base_cache_dir):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    stats = os.stat(filepath)
                    total_size += stats.st_size
                    files_with_stats.append((filepath, stats.st_mtime, stats.st_size))
                except OSError:
                    continue

        if total_size > self.MAX_CACHE_SIZE_BYTES:
            print(f"[Cache] Size limit exceeded ({total_size / (1024*1024):.2f} MB). Cleaning up...")
            # Sort by modification time, oldest first
            files_with_stats.sort(key=lambda x: x[1])
            
            for filepath, _, size in files_with_stats:
                try:
                    os.remove(filepath)
                    total_size -= size
                    if total_size <= self.MAX_CACHE_SIZE_BYTES * 0.9: # Clean down to 90%
                        break
                except OSError:
                    continue
            print(f"[Cache] Cleanup complete. New size: {total_size / (1024*1024):.2f} MB")

cache_service = CacheService()
