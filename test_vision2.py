import urllib.request
import json
import base64

api_key = "sk-YSOaE1QIsyyUmwkn9EavAsRjZ0D6A63dNIe0SBZVV8R"
url = "https://aimodel.lol/v1/responses"

def test_payload(model_id):
    base64_img = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAANSURBVBhXY3jP4PgfAAWgA4E9Q6PMAAAAAElFTkSuQmCC"
    image_url = f"data:image/png;base64,{base64_img}"
    payload = {
        "model": model_id,
        "input": [
            {"role": "system", "content": "You are a helpful assistant."}, 
            {"role": "user", "content": [
                {"type": "input_text", "text": "What color is this one pixel image?"},
                {"type": "input_image", "image_url": image_url}
            ]}
        ],
        "temperature": 0.5,
        "max_output_tokens": 100
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        if hasattr(e, 'read'):
            return f"HTTP {e.code}: " + e.read().decode('utf-8')
        return str(e)

print("fable-5:", test_payload("fable-5"))
print("accounts/aimodel/models/glm-5.2-vision:", test_payload("accounts/aimodel/models/glm-5.2-vision"))
