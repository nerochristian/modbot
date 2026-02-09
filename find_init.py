
with open('database.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'def init_guild' in line:
            print(f"Found at line {i+1}: {line.strip()}")
