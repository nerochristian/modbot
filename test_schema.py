import json
with open('schema.json', 'r', encoding='utf-8') as f:
    schema = json.load(f)
import pprint
defs = schema.get('$defs', {})
pprint.pprint(defs.get('ProviderConfig', {}).get('properties', {}).get('models', {}))
