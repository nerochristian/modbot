import os

for root, dirs, files in os.walk('cogs'):
    for f in files:
        if not f.endswith('.py'):
            continue
        filepath = os.path.join(root, f)
        with open(filepath, encoding='utf-8') as fh:
            for i, line in enumerate(fh, 1):
                stripped = line.strip()
                if ('"mod"' in stripped or "'mod'" in stripped) and ('Group' in stripped or 'add_command' in stripped or 'Command(' in stripped):
                    print(f'{filepath}:{i}:{stripped}')
                if ('"moderation"' in stripped or "'moderation'" in stripped) and ('Group' in stripped or 'add_command' in stripped or 'Command(' in stripped):
                    print(f'{filepath}:{i}:{stripped}')