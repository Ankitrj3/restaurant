import urllib3
urllib3.disable_warnings()
import requests
import json

p = """
Find at least 10 real Indian, Pakistani, Nepalese, or Bengali restaurants within a 20 mile radius of 30.568, -97.802.
Return EXACTLY this JSON structure:
[
  {
    "name": "...",
    "address": "...",
    "phone": "...",
    "website_url": "...",
    "latitude": 0.0,
    "longitude": 0.0,
    "cuisine_tags": ["Indian"]
  }
]
"""

payload = {
    'contents': [{'parts': [{'text': p}]}],
    'generationConfig': {
        'responseMimeType': 'application/json',
        'maxOutputTokens': 2048
    }
}

r = requests.post(
    'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=AIzaSyDyX7jgphillIuIuaOXP-6QOy4YLlpiJQI',
    json=payload,
    verify=False
)
print(json.dumps(r.json(), indent=2))
