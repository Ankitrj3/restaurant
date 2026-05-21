import sys
import os
import requests
import json
import dotenv

dotenv.load_dotenv('/Users/ankitrj3/Desktop/restaurant/.env')
api_key = os.getenv('ANTHROPIC_API_KEY')

print(f"Using Anthropic API Key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 4 else ''}")

url = "https://api.anthropic.com/v1/messages"
headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

payload = {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 100,
    "messages": [
        {"role": "user", "content": "Hello, how are you? Return JSON: {\"reply\": \"hi\"}"}
    ]
}

print("\n--- Testing Anthropic Call ---")
try:
    resp = requests.post(url, json=payload, headers=headers, verify=False, timeout=10)
    print("Status Code:", resp.status_code)
    print("Response text:", resp.text)
except Exception as e:
    print("Error:", e)
