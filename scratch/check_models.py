import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")

api_key = os.getenv("AIMODEL_API_KEY")
base_url = "https://aimodel.lol/v1"

if not api_key:
    print("No API key found in .env for AIMODEL_API_KEY")
else:
    try:
        response = requests.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        response.raise_for_status()
        models = response.json().get("data", [])
        for model in models:
            print(f"- {model.get('id')}")
    except Exception as e:
        print(f"Error fetching models: {e}")
