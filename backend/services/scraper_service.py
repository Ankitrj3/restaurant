"""
Web scraping service for extracting restaurant data from multiple platforms.
Uses BeautifulSoup for HTML parsing and Playwright for dynamic pages.
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from config import Config


class ScraperService:
    """Multi-platform restaurant data scraper."""

    def __init__(self):
        import urllib3
        urllib3.disable_warnings()
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def search_google_restaurants(self, query, location):
        """Search for Indian restaurants near the location via Google."""
        search_query = f"{query} near {location}"
        url = f"https://www.google.com/search?q={requests.utils.quote(search_query)}&num=20"
        try:
            resp = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            soup = BeautifulSoup(resp.text, 'lxml')
            restaurants = []
            for result in soup.select('.VkpGBb, .rllt__details'):
                name_el = result.select_one('.dbg0pd, .OSrXXb')
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                if self._is_excluded(name):
                    continue
                restaurant = {'name': name, 'address': '', 'rating': 0, 'total_reviews': 0, 'price_category': '$$', 'source': 'google'}
                rating_el = result.select_one('.yi40Hd, .Y0A0hc')
                if rating_el:
                    try:
                        restaurant['rating'] = float(rating_el.get_text(strip=True))
                    except ValueError:
                        pass
                restaurants.append(restaurant)
            return restaurants
        except Exception as e:
            print(f"[Scraper] Google search error: {e}")
            return []

    def search_yelp_restaurants(self, location, cuisine='Indian'):
        """Search Yelp for Indian restaurants near the location."""
        url = f"https://www.yelp.com/search?find_desc={cuisine}+restaurants&find_loc={requests.utils.quote(location)}"
        try:
            resp = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            soup = BeautifulSoup(resp.text, 'lxml')
            restaurants = []
            for card in soup.select('[data-testid="serp-ia-card"]'):
                name_el = card.select_one('h3 a, h4 a')
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                if self._is_excluded(name):
                    continue
                restaurant = {'name': name, 'address': '', 'rating': 0, 'total_reviews': 0, 'price_category': '$$', 'source': 'yelp'}
                restaurants.append(restaurant)
            return restaurants
        except Exception as e:
            print(f"[Scraper] Yelp search error: {e}")
            return []

    def extract_menu_from_url(self, url):
        """Extract menu data from a restaurant URL. Returns raw content for AI processing."""
        try:
            resp = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            soup = BeautifulSoup(resp.text, 'lxml')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            menu_content = self._find_menu_section(soup)
            return {'url': url, 'content': menu_content, 'title': soup.title.get_text(strip=True) if soup.title else '', 'success': True}
        except Exception as e:
            print(f"[Scraper] Menu extraction error for {url}: {e}")
            return {'url': url, 'content': '', 'title': '', 'success': False}

    def extract_menu_with_playwright(self, url):
        """Extract menu from dynamic pages using Playwright (Disabled due to EPIPE crash)."""
        print(f"[Scraper] Playwright is disabled on this machine to prevent crashes. Using fallback for {url}")
        return self.extract_menu_from_url(url)

    def extract_offers_from_page(self, url):
        """Extract offers and promotions from a page."""
        try:
            resp = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            soup = BeautifulSoup(resp.text, 'lxml')
            offers = []
            keywords = ['off', 'discount', 'deal', 'combo', 'special', 'free delivery', 'bogo', 'buy 1 get 1', 'coupon', 'promo', 'save', '%']
            for el in soup.find_all(text=True):
                text = el.strip().lower()
                if any(kw in text for kw in keywords) and len(text) > 10:
                    offers.append(el.strip())
            return {'url': url, 'raw_offers': offers[:20], 'success': True}
        except Exception as e:
            return {'url': url, 'raw_offers': [], 'success': False}

    def _find_menu_section(self, soup):
        """Try to locate the menu section in parsed HTML."""
        for selector in ['#menu', '.menu', '.menu-section', '.food-menu', '.menu-container']:
            menu = soup.select_one(selector)
            if menu:
                return menu.get_text(separator='\n', strip=True)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Restaurant', 'Menu']:
                    return json.dumps(data, indent=2)
            except (json.JSONDecodeError, TypeError):
                pass
        main = soup.select_one('main, [role="main"], .content, #content')
        if main:
            return main.get_text(separator='\n', strip=True)[:10000]
        return soup.get_text(separator='\n', strip=True)[:10000]

    def _is_excluded(self, name):
        """Check if a restaurant should be excluded from results."""
        excluded = [
            'bawarchi biryanis',
            'bawarchi biryani',
            'bawarchi indian cuisine & bar leander',
        ]
        return name.lower().strip() in excluded


scraper_service = ScraperService()
