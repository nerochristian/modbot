import os, re

for root, dirs, files in os.walk('cogs'):
    for f in files:
        if not f.endswith('.py'):
            continue
        filepath = os.path.join(root, f)
        with open(filepath, encoding='utf-8') as fh:
            for i, line in enumerate(fh, 1):
                stripped = line.strip()
                # Look for any slash group named "mod" or "moderation"
                m = re.search(r'app_commands\.Group\(name=["\']([^"\']+)["\']', stripped)
                if m and m.group(1) in ('mod', 'moderation'):
                    print(f'{filepath}:{i}:{stripped}')
                # Also look for add_command with mod/moderation
                if 'add_command' in stripped and ('"mod"' in stripped or "'mod'" in stripped or '"moderation"' in stripped or "'moderation'" in stripped):
                    print(f'{filepath}:{i}:{stripped}')
                # Look for Command( with mod/moderation
                if 'Command(' in stripped and ('"mod"' in stripped or "'mod'" in stripped or '"moderation"' in stripped or "'moderation'" in stripped):
                    print(f'{filepath}:{i}:{stripped}')