import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from services.competitor_service import competitor_service
from services.cache_service import cache_service
from config import Config

class BackgroundJobManager:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._is_running = False

    def start(self):
        if self._is_running:
            return

        print("[Scheduler] Starting background jobs...")
        
        # 1. Competitor discovery -> every 24 hours
        self.scheduler.add_job(
            func=self.refresh_discovery,
            trigger=IntervalTrigger(hours=24),
            id='refresh_discovery',
            name='Refresh Competitor Discovery',
            replace_existing=True
        )

        # 2. Uber/DoorDash/Grubhub menus -> every 4 hours
        self.scheduler.add_job(
            func=self.refresh_menus,
            trigger=IntervalTrigger(hours=4),
            id='refresh_menus',
            name='Refresh Competitor Menus',
            replace_existing=True
        )

        # 3. Delivery fees -> every 15 minutes
        # Note: Handled dynamically or via platform_service integration.
        # Here we trigger a cache clean/refresh logic if needed.

        # 4. Cache Cleanup -> every hour to enforce the 1GB limit
        self.scheduler.add_job(
            func=self.cleanup_cache,
            trigger=IntervalTrigger(hours=1),
            id='cleanup_cache',
            name='Enforce Cache Size Limits',
            replace_existing=True
        )

        self.scheduler.start()
        self._is_running = True
        print("[Scheduler] Background jobs started successfully.")

    def refresh_discovery(self):
        print("[Scheduler] Running scheduled competitor discovery refresh...")
        try:
            # Pass max_radius=20 or from config
            competitor_service.find_competitors(max_radius=20)
        except Exception as e:
            print(f"[Scheduler] Discovery refresh failed: {e}")

    def refresh_menus(self):
        print("[Scheduler] Running scheduled menu refresh...")
        try:
            # We can use the cache to find known restaurants and re-fetch them
            cache_key = f"20_{Config.CLIENT_LAT}_{Config.CLIENT_LNG}"
            cached_discovery = cache_service.get_latest('discovery', cache_key)
            if cached_discovery and 'restaurants' in cached_discovery:
                for r in cached_discovery['restaurants']:
                    # Re-fetch menu live (this will update the cache)
                    competitor_service.get_restaurant_menu(r)
                    time.sleep(2) # Be polite to APIs
        except Exception as e:
            print(f"[Scheduler] Menu refresh failed: {e}")

    def cleanup_cache(self):
        print("[Scheduler] Running cache cleanup enforcement...")
        try:
            cache_service._enforce_size_limit()
        except Exception as e:
            print(f"[Scheduler] Cache cleanup failed: {e}")

background_jobs = BackgroundJobManager()
