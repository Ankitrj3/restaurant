import sys
import os
import requests
import json
import dotenv

dotenv.load_dotenv('/Users/ankitrj3/Desktop/restaurant/.env')
api_key = os.getenv('GEMINI_API_KEY')

print(f"Using API Key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 4 else ''}")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

# Non-grounded payload
payload_non_grounded = {
    "contents": [{
        "parts": [{"text": "Hello, how are you? Return JSON: {\"reply\": \"hi\"}"}]
    }],
    "generationConfig": {
        "temperature": 0.1,
        "maxOutputTokens": 100,
        "responseMimeType": "application/json"
    }
}

print("\n--- Testing Non-Grounded Call ---")
try:
    resp = requests.post(url, json=payload_non_grounded, headers={'Content-Type': 'application/json'}, verify=False, timeout=10)
    print("Status Code:", resp.status_code)
    print("Response text:", resp.text)
except Exception as e:
    print("Error:", e)

# Grounded payload
payload_grounded = {
    "contents": [{
        "parts": [{"text": "Search Google for Bawarchi Indian Cuisine Leander TX address. Return JSON: {\"address\": \"address_here\"}"}]
    }],
    "tools": [
        {"google_search": {}}
    ],
    "generationConfig": {
        "temperature": 0.1,
        "maxOutputTokens": 200
    }
}

print("\n--- Testing Grounded Call ---")
try:
    resp = requests.post(url, json=payload_grounded, headers={'Content-Type': 'application/json'}, verify=False, timeout=15)
    print("Status Code:", resp.status_code)
    print("Response text:", resp.text)
except Exception as e:
    print("Error:", e)
