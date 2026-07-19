import os
import re
from pathlib import Path

assets_dir = Path(r"C:\Users\Dell\mod\assets")

for svg_file in assets_dir.glob("emoji_*.svg"):
    content = svg_file.read_text(encoding="utf-8")
    
    # Extract the base name to make the ID unique (e.g., emoji_bot -> bot)
    base_name = svg_file.stem.replace("emoji_", "")
    new_shadow_id = f"shadow_{base_name}"
    
    # Replace id="shadow" and url(#shadow)
    # Be careful not to replace multiple times if already replaced
    if 'id="shadow"' in content or "url(#shadow)" in content:
        new_content = content.replace('id="shadow"', f'id="{new_shadow_id}"')
        new_content = new_content.replace('url(#shadow)', f'url(#{new_shadow_id})')
        
        svg_file.write_text(new_content, encoding="utf-8")
        print(f"Fixed shadow ID in {svg_file.name} to {new_shadow_id}")

print("Done fixing SVG shadow IDs.")
