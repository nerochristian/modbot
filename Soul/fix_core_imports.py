import os

filepath = r'c:\Users\Dell\Soul\guild\economy\core.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The mangled part is from line 18 (index 17) to where `_fit_text,` is found (index 37).
# Actually, the original imports up to _fit_text were:

original_imports = """import discord
from discord.ext import commands
from discord.ext import tasks
import psycopg2
import psycopg2.extras
from .cache import ttl_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from level_system import (
    _card_file,
    _rep_card_file,
    _star_polygon,
    _background_data_from_settings,
    _circle_avatar,
    _download_image_bytes,
"""

# Let's find where `_fit_text,` is (around line 38)
fit_text_idx = -1
for i, line in enumerate(lines):
    if '_fit_text,' in line:
        fit_text_idx = i
        break

if fit_text_idx != -1:
    new_lines = lines[:16] + [original_imports] + lines[fit_text_idx:]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Fixed core.py locally!")
else:
    print("Could not find _fit_text,")
