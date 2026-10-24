"""Check that the Gemini API key in .env works with Gemma 4.

Run:  python check_key.py
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()
key = (os.getenv("GEMINI_API_KEY") or "").strip().strip('"').strip("'")
MODEL = "gemma-4-26b-a4b-it"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

if not key or key.upper().startswith("PASTE"):
    print("No key found. Open the .env file in this folder and replace PASTE_YOUR_KEY_HERE with your key, then save.")
    raise SystemExit(1)

print(f"Key loaded: {key[:5]}... ({len(key)} characters)")
body = {"contents": [{"parts": [{"text": "Reply with the single word: OK"}]}]}
styles = {
    "header": ({"x-goog-api-key": key}, {}),
    "query": ({}, {"key": key}),
    "bearer": ({"Authorization": f"Bearer {key}"}, {}),
}
for name, (headers, params) in styles.items():
    try:
        r = requests.post(URL, headers=headers, params=params, json=body, timeout=30)
    except requests.RequestException as e:
        print(f"  {name:6} -> no connection ({e.__class__.__name__})")
        continue
    if r.ok:
        print(f"  {name:6} -> 200 OK. Gemma 4 is working. Start the site with: python -m streamlit run score_face.py")
        raise SystemExit(0)
    print(f"  {name:6} -> {r.status_code}: {r.text[:160].strip()}")

print("Google refused the key every way. Check you copied the whole key from aistudio.google.com.")
raise SystemExit(1)
