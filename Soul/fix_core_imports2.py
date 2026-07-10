import os

filepath = r'c:\Users\Dell\Soul\guild\economy\core.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('    _rep_card_file,\n', '')
content = content.replace('    _star_polygon,\n', '')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Removed _rep_card_file and _star_polygon")
