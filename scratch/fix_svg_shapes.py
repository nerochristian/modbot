import re
from pathlib import Path

assets_dir = Path(r"C:\Users\Dell\mod\assets")

template = """<svg width="128" height="128" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <defs>
    {gradient}
    <filter id="{shadow_id}" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="1" stdDeviation="1" flood-color="#000" flood-opacity="0.3"/>
    </filter>
  </defs>

  <g transform-origin="12 12">
    <animateTransform attributeName="transform" type="scale" values="1; 1.04; 1; 1" keyTimes="0; 0.15; 0.3; 1" dur="2.5s" repeatCount="indefinite" calcMode="spline" keySplines="0.4 0 0.2 1; 0.4 0 0.2 1; 0 0 1 1"/>
    
    <path d="M12 2L4 6V11C4 16 7.5 19.5 12 22C16.5 19.5 20 16 20 11V6L12 2Z" fill="url(#{grad_id})" filter="url(#{shadow_id})"/>
    <path d="M12 2.5L4.5 6.3V11C4.5 15.6 7.8 18.9 12 21.2C16.2 18.9 19.5 15.6 19.5 11V6.3L12 2.5Z" fill="none" stroke="white" stroke-opacity="0.2" stroke-width="0.5"/>

    {inner_g}
  </g>
</svg>"""

count = 0
for svg_file in assets_dir.glob("emoji_*.svg"):
    content = svg_file.read_text(encoding="utf-8")
    
    if svg_file.name in ["emoji_warn.svg", "emoji_ban.svg", "emoji_error.svg", "emoji_success.svg", "emoji_info.svg", "emoji_kick.svg", "emoji_mute.svg", "emoji_lock.svg", "emoji_unlock.svg", "emoji_verification.svg"]:
        # Skip the ones that are already good or don't use this template
        continue
        
    print(f"Fixing {svg_file.name}...")
    
    # Extract linearGradient
    grad_match = re.search(r'<linearGradient id="([^"]+)".*?</linearGradient>', content)
    if not grad_match:
        print(f"Could not find linearGradient in {svg_file.name}, skipping.")
        continue
        
    grad_id = grad_match.group(1)
    gradient_str = grad_match.group(0)
    
    # Ensure gradient string uses nice formatting for stops
    gradient_str = re.sub(r'<stop ', '\n      <stop ', gradient_str)
    gradient_str = re.sub(r'</linearGradient>', '\n    </linearGradient>', gradient_str)
    
    # Extract inner g
    inner_g = ""
    if 'stroke-width=".5"/>' in content:
        tail = content.split('stroke-width=".5"/>')[1]
        tail = re.sub(r'</g>\s*</svg>\s*$', '', tail)
        inner_g = tail.strip()
    else:
        print(f"Could not find inner icon delimiter in {svg_file.name}, skipping.")
        continue
        
    # Replace the opacity animation to match the static hold of `warn` / `ban`
    # This prevents the GIF from having 75 unique frames and exceeding the 256KB limit!
    bad_anim = r'<animate attributeName="opacity" values="[^"]+" dur="2.5s" repeatCount="indefinite"/>'
    good_anim = '<animate attributeName="opacity" values="0.75; 1; 1; 0.75" keyTimes="0; 0.15; 0.85; 1" dur="2.5s" repeatCount="indefinite" />'
    inner_g = re.sub(bad_anim, good_anim, inner_g)
    
    # Ensure inner_g animation is formatted somewhat nicely
    inner_g = re.sub(r'<animate attributeName', '\n      <animate attributeName', inner_g)
    # Add indent to inner_g
    inner_g = "\n    ".join(inner_g.split("\n"))
    
    base_name = svg_file.stem.replace("emoji_", "")
    shadow_id = f"shadow_{base_name}"
    
    new_content = template.format(
        gradient=gradient_str,
        shadow_id=shadow_id,
        grad_id=grad_id,
        inner_g=inner_g
    )
    
    svg_file.write_text(new_content, encoding="utf-8")
    count += 1

print(f"Fixed {count} SVGs.")
