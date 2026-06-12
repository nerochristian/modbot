import os
import json
import re
from bs4 import BeautifulSoup

html_path = r'C:\Users\Dell\Downloads\Nova - Discord Bot.html'
html = open(html_path, encoding='utf-8').read()

soup = BeautifulSoup(html, 'html.parser')

# Extract styles from head
styles = soup.head.find_all('style')
css_content = "\n".join([style.string for style in styles if style.string])

# Get body content
body = soup.body
for tag in body(['script', 'noscript']):
    tag.decompose()
body_content = body.decode_contents()

# Define color replacements (Dark/Purple to Light/Blue)
replacements = [
    # Purples to Blues
    ('rgb(104, 31, 209)', 'rgb(37, 134, 255)'),
    ('rgb(138, 31, 209)', 'rgb(96, 165, 250)'),
    ('rgb(69, 18, 113)', 'rgb(30, 58, 138)'),
    ('rgb(134, 28, 169)', 'rgb(59, 130, 246)'),
    ('rgb(49, 23, 88)', 'rgb(23, 37, 84)'),
    ('#681fd1', '#2586ff'),
    ('#5C1BB8', '#1e40af'),
    ('#7A33E0', '#3b82f6'),
    
    # Dark backgrounds to Light/White
    ('rgb(8, 8, 15)', 'rgb(255, 255, 255)'),
    ('rgb(24, 24, 32)', 'rgb(240, 248, 255)'),
    ('rgb(20, 20, 27)', 'rgb(248, 250, 252)'),
    ('rgb(10, 3, 20)', 'rgb(248, 250, 252)'),
    ('#0f0f19', '#f8fafc'),
    ('#12131c', '#ffffff'),
    ('#15161f', '#f1f5f9'),
    ('#2A2C33', '#e2e8f0'),
    ('#3A3D46', '#cbd5e1'),
    
    # Text colors
    ('color: rgb(255, 255, 255)', 'color: rgb(15, 23, 42)'),
    ('color: #ffffff', 'color: #0f172a'),
    ('fill="#ffffff"', 'fill="#0f172a"'),
    ('color="#ffffff"', 'color="#0f172a"'),
    
    # Fix the MUI paper overlay which causes dark shading
    ('linear-gradient(rgba(255, 255, 255, 0.092), rgba(255, 255, 255, 0.092))', 'none'),
]

# Apply replacements to CSS and HTML
for old, new in replacements:
    css_content = css_content.replace(old, new)
    body_content = body_content.replace(old, new)

# Write CSS
with open(r'C:\Users\Dell\mod\website\src\pages\nova-styles.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

# Write JS HTML string
js_content = f"export const novaHtml = {json.dumps(body_content)};\n"
with open(r'C:\Users\Dell\mod\website\src\pages\novaHtml.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

# Write Landing.jsx
jsx_template = """import React, { useEffect } from 'react';
import './Landing.css';
import './nova-styles.css'; // Mui styles from original document
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

print("Fix applied.")
