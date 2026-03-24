import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={
        "temperature": 0.3,
        "response_mime_type": "application/json"
    }
)

def suggest_cities_ai(query: str, limit: int = 4):
    prompt = f'''
You are a location autocomplete engine.

User input: "{query}"

Rules:
- Suggest real cities or well-known settlements
- Sort by global popularity and common usage
- Return between 3 and {limit} results
- Prefer internationally known cities first
- Output ONLY valid JSON
- No explanations

JSON format:
{{
  "suggestions": [
    "City, Country"
  ]
}}
'''
    response = model.generate_content(prompt)
    return json.loads(response.text)["suggestions"]

