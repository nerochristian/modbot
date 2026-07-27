import json
import urllib.request

api_key = "sk-YSOaE1QIsyyUmwkn9EavAsRjZ0D6A63dNIe0SBZVV8R"
url = "https://aimodel.lol/v1/models"

req = urllib.request.Request(url, headers={
    'Authorization': f'Bearer {api_key}',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        
        models_dict = {}
        for model in data.get('data', []):
            model_id = model.get('id')
            models_dict[model_id] = {
                "name": f"AiModel ({model_id.split('/')[-1]})"
            }
            
        config = {
            "$schema": "https://opencode.ai/config.json",
            "provider": {
                "aimodel": {
                    "api": "openai",
                    "options": {
                        "baseURL": "https://aimodel.lol/v1",
                        "apiKey": api_key
                    },
                    "models": models_dict
                }
            },
            "model": "aimodel:accounts/aimodel/models/claude-fable-5",
            "small_model": "aimodel:accounts/aimodel/models/kimi-k3-fast"
        }
        
        config_path = r'C:\Users\Smart Room 1\.config\opencode\opencode.jsonc'
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
            
        print("Config updated successfully")
except Exception as e:
    print(f"Error: {e}")
