import json
from bs4 import BeautifulSoup

html = open(r'C:\Users\Dell\Downloads\Nova - Discord Bot.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')

# Get the body content
body = soup.body

# Remove unwanted scripts and extra stuff if any
for tag in body(['script', 'noscript']):
    tag.decompose()

body_content = body.decode_contents()

# Create a JS file that exports this string
js_content = f"export const novaHtml = {json.dumps(body_content)};\n"

with open(r'C:\Users\Dell\mod\website\src\pages\novaHtml.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

# Now generate Landing.jsx
jsx_template = """import React, { useEffect } from 'react';
import './Landing.css';
import { novaHtml } from './novaHtml';

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
    <div className="nova-override-light" dangerouslySetInnerHTML={{ __html: novaHtml }} />
  );
}
"""

with open(r'C:\Users\Dell\mod\website\src\pages\Landing.jsx', 'w', encoding='utf-8') as f:
    f.write(jsx_template)

print("Done creating novaHtml.js and Landing.jsx via dangerouslySetInnerHTML")
