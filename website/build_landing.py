import os
import shutil
import re
from bs4 import BeautifulSoup

# 1. Copy assets to public
src_dir = r'C:\Users\Dell\Downloads\Nova - Discord Bot_files'
dest_dir = r'C:\Users\Dell\mod\website\public\Nova - Discord Bot_files'
if not os.path.exists(dest_dir):
    shutil.copytree(src_dir, dest_dir)

# 2. Read the raw HTML
html = open(r'C:\Users\Dell\Downloads\Nova - Discord Bot.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')

# Remove unwanted head stuff and scripts
for tag in soup(['script', 'noscript', 'link', 'meta', 'title', 'style']):
    tag.decompose()

# Function to camel case SVG and React attributes
def camel_case(s):
    parts = s.split('-')
    return parts[0] + ''.join(x.title() for x in parts[1:])

react_attrs = {
    'class': 'className',
    'for': 'htmlFor',
    'stroke-width': 'strokeWidth',
    'stroke-linecap': 'strokeLinecap',
    'stroke-linejoin': 'strokeLinejoin',
    'stroke-miterlimit': 'strokeMiterlimit',
    'stroke-dasharray': 'strokeDasharray',
    'stroke-dashoffset': 'strokeDashoffset',
    'font-family': 'fontFamily',
    'font-weight': 'fontWeight',
    'font-size': 'fontSize',
    'text-anchor': 'textAnchor',
    'fill-rule': 'fillRule',
    'clip-rule': 'clipRule',
    'stroke-opacity': 'strokeOpacity',
    'fill-opacity': 'fillOpacity',
    'color-interpolation-filters': 'colorInterpolationFilters',
    'stop-color': 'stopColor',
    'stop-opacity': 'stopOpacity',
    'xmlns:xlink': 'xmlnsXlink',
    'xml:space': 'xmlSpace',
    'viewbox': 'viewBox',
    'preserveaspectratio': 'preserveAspectRatio',
    'tabindex': 'tabIndex'
}

for tag in soup.find_all(True):
    attrs = list(tag.attrs.items())
    for k, v in attrs:
        # Beautifulsoup lowercases everything, but our react_attrs dict handles the ones we care about
        new_k = react_attrs.get(k)
        if not new_k and '-' in k and not k.startswith('data-') and not k.startswith('aria-'):
            new_k = camel_case(k)
            
        if new_k:
            tag[new_k] = ' '.join(v) if isinstance(v, list) else v
            del tag[k]
        elif k == 'class':
            tag['className'] = ' '.join(v) if isinstance(v, list) else v
            del tag[k]
        elif k == 'for':
            tag['htmlFor'] = v
            del tag[k]
        
        # Safe style removal
        if (new_k == 'style' or k == 'style') and isinstance(v, str):
            del tag['style']
            
        # Quick fix for boolean attributes in React
        if tag.get(k) == '':
            tag[k] = 'true'

body = soup.body

jsx_template = """import React, { useEffect } from 'react';
import './Landing.css';

export default function Landing() {
  useEffect(() => {
    // Add Nova CSS links dynamically
    const cssFiles = [
      '/Nova - Discord Bot_files/2ed203cab694de14.css',
      '/Nova - Discord Bot_files/e2ff4a437874c524.css',
      '/Nova - Discord Bot_files/a4b6c8894dd9e81a.css'
    ];
    
    cssFiles.forEach(href => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;
      link.dataset.nova = 'true';
      document.head.appendChild(link);
    });
    
    return () => {
      document.querySelectorAll("link[data-nova='true']").forEach(el => el.remove());
    };
  }, []);

  return (
    <div className="nova-override-light">
      {CONTENT}
    </div>
  );
}
"""

content = body.decode_contents()
# Fix html comments
content = content.replace('<!--$-->', '{/* $ */}').replace('<!--/$-->', '{/* /$ */}')
# Fix self closing tags
content = re.sub(r'<img(.*?)(?<!/)>', r'<img\1 />', content)
content = re.sub(r'<br(.*?)(?<!/)>', r'<br\1 />', content)
content = re.sub(r'<hr(.*?)(?<!/)>', r'<hr\1 />', content)
content = re.sub(r'<input(.*?)(?<!/)>', r'<input\1 />', content)
content = re.sub(r'<source(.*?)(?<!/)>', r'<source\1 />', content)

# Remove HTML comments using regex
content = re.sub(r'<!--(.*?)-->', r'{/* \1 */}', content)

jsx_output = jsx_template.replace('{CONTENT}', content)

with open(r'C:\Users\Dell\mod\website\src\pages\Landing.jsx', 'w', encoding='utf-8') as f:
    f.write(jsx_output)

print("Done")
