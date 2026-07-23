import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")

api_key = os.getenv("AIMODEL_API_KEY")
base_url = "https://aimodel.lol/v1"

# A specific string that tokenizes very differently across models.
# For example, Chinese text is highly compressed by GLM and DeepSeek, 
# but takes many more tokens in Claude or older OpenAI models.
test_string = "Hello world! " * 50 + "你好世界！" * 50

models_to_test = [
    "accounts/aimodel/models/glm-5.1",
    "accounts/aimodel/models/claude-opus-4.8",
    "accounts/aimodel/models/deepseek-v4-pro"
]

questions = [
    {"role": "user", "content": test_string}
]

print("Running Tokenizer Identity Check...")
print("-" * 40)

for model in models_to_test:
    print(f"Testing {model}...")
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": questions,
                "max_tokens": 10,
                "temperature": 0
            }
        )
        if response.status_code == 200:
            usage = response.json().get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 'Unknown')
            print(f"Prompt Tokens: {prompt_tokens}")
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Failed: {e}")
    print("-" * 40)
