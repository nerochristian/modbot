# Extract sections from the aimoderation monolith and write modular files
monolith_path = 'cogs/aimoderation/aimoderation.py'

with open(monolith_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# --- Locate boundaries ---
gemini_start = next(i for i, l in enumerate(lines) if l.startswith('class GeminiClient:'))
aimod_start = next(i for i, l in enumerate(lines) if l.startswith('class AIModeration(commands.Cog):'))
setup_line = next(i for i, l in enumerate(lines) if l.strip().startswith('async def setup(bot:') and 'None' in l)

# Find where AIModeration class body starts (past the ClassVar definitions)
init_line = next(i for i in range(aimod_start, len(lines)) if lines[i].strip().startswith('def __init__') and 'bot: commands.Bot' in lines[i])

print(f"GeminiClient: lines {gemini_start+1}-{aimod_start} ({aimod_start-gemini_start} lines)")
print(f"AIModeration ClassVar block: lines {aimod_start+1}-{init_line}")
print(f"AIModeration __init__ onward: lines {init_line+1}-{setup_line} ({setup_line-init_line} lines)")
print(f"setup: line {setup_line+1}")

# Find key method boundaries within AIModeration
methods = {}
for i in range(aimod_start, setup_line):
    ls = lines[i].strip()
    if ls.startswith('def ') or ls.startswith('async def '):
        name = ls.split('(')[0].replace('async def ', '').replace('def ', '')
        if name.startswith('_') or name in ('cog_load', 'cog_unload', 'clean_content', 'extract_mentions', 'fetch_recent_messages'):
            methods[name] = i

for name, line_num in sorted(methods.items(), key=lambda x: x[1]):
    print(f"  {name}: line {line_num+1}")

# Extract the full GeminiClient
gemini_lines = lines[gemini_start:aimod_start]
# Find where the inner GeminiClient class ends (next class/top-level def)
for i in range(aimod_start + 1, len(lines)):
    if lines[i].startswith('class ') and not lines[i].startswith('    '):
        break

print(f"\nDone. GeminiClient is {len(gemini_lines)} lines starting from line {gemini_start+1}")
print(f"Total file: {len(lines)} lines")
