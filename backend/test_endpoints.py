import urllib3
urllib3.disable_warnings()
import requests, json

BASE = 'http://localhost:5050'

def test(name, url):
    try:
        r = requests.get(f'{BASE}{url}', verify=False, timeout=30)
        data = r.json()
        if isinstance(data, list):
            print(f"  OK {name}: {len(data)} items (array)")
            if data:
                print(f"      Keys: {list(data[0].keys())[:5]}")
        elif isinstance(data, dict):
            keys = list(data.keys())[:6]
            print(f"  OK {name}: dict({keys})")
        else:
            print(f"  OK {name}: {type(data)}")
    except Exception as e:
        print(f"  FAIL {name}: {e}")

print("=== ENDPOINT TESTS ===")
test("Health", "/api/health")
test("Search", "/api/restaurants/search?radius=20")
test("Client Menu", "/api/client/menu")
test("Restaurants List", "/api/restaurants/list")
test("Categories", "/api/categories")
test("Platforms", "/api/platforms")
test("In-Store Compare", "/api/comparison/instore")
test("UberEats Compare", "/api/comparison/platform/ubereats")
test("DoorDash Compare", "/api/comparison/platform/doordash")
test("Grubhub Compare", "/api/comparison/platform/grubhub")
test("Delivery Compare", "/api/comparison/delivery")
test("Free Delivery", "/api/platforms/free-delivery")
test("Category Biryani", "/api/comparison/category/Biryani?platform=instore")
print("\n=== ALL TESTS COMPLETE ===")
