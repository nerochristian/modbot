import urllib.request
import json

api_key = "sk-KdGb0sOpgENfT95QRhDerqwGQLBZAHyA4nlJ1vGmg44"
url = "https://aimodel.lol/v1/models"

req = urllib.request.Request(url, headers={'Authorization': f'Bearer {api_key}'})
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        
        opencode_models = []
        for model in data.get('data', []):
            model_id = model.get('id')
            opencode_models.append({
                "title": f"AiModel ({model_id.split('/')[-1]})",
                "provider": "openai",
                "model": model_id,
                "apiKey": api_key,
                "apiBase": "https://aimodel.lol/v1"
            })
            
        config = {
            "$schema": "https://opencode.ai/config.json",
            "models": opencode_models
        }
        
        with open(r'C:\Users\Smart Room 1\.config\opencode\opencode.jsonc', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
            
        print(f"Successfully added {len(opencode_models)} models to opencode.jsonc")
except Exception as e:
    print(f"Error: {e}")
