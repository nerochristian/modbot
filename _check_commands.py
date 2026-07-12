import os, re

# Find all app_commands.Group definitions and check for duplicates
group_defs = {}  # name -> list of (file, line)
group_cmds = []  # (file, line, group_name, cmd_name)

for root, dirs, files in os.walk('cogs'):
    for f in files:
        if not f.endswith('.py'):
            continue
        filepath = os.path.join(root, f)
        with open(filepath, encoding='utf-8') as fh:
            for i, line in enumerate(fh, 1):
                stripped = line.strip()
                # Find Group definitions
                m = re.search(r'app_commands\.Group\(name=["\']([^"\']+)["\']', stripped)
                if m:
                    name = m.group(1)
                    if name not in group_defs:
                        group_defs[name] = []
                    group_defs[name].append((filepath, i))

                # Find @group.command definitions
                m2 = re.search(r'@(\w+)\.command\(name=["\']([^"\']+)["\']', stripped)
                if m2:
                    group_cmds.append((filepath, i, m2.group(1), m2.group(2)))

                # Find app_commands.command definitions
                m3 = re.search(r'@app_commands\.command\(name=["\']([^"\']+)["\']', stripped)
                if m3:
                    group_cmds.append((filepath, i, 'TOPLEVEL', m3.group(1)))

                # Find app_commands.Command (manual registration)
                m4 = re.search(r'app_commands\.Command\(name=["\']([^"\']+)["\']', stripped)
                if m4:
                    group_cmds.append((filepath, i, 'MANUAL', m4.group(1)))

print("=== GROUP DEFINITIONS ===")
for name, locations in sorted(group_defs.items()):
    if len(locations) > 1:
        print(f"DUPLICATE GROUP '{name}':")
        for f, l in locations:
            print(f"  {f}:{l}")
    else:
        print(f"Group '{name}': {locations[0][0]}:{locations[0][1]}")

print("\n=== ALL COMMAND NAMES (top-level and group subcommands) ===")
cmd_locations = {}
for f, l, group, name in group_cmds:
    key = f"{group}/{name}" if group not in ('TOPLEVEL', 'MANUAL') else name
    if key not in cmd_locations:
        cmd_locations[key] = []
    cmd_locations[key].append((f, l))

print("\n=== DUPLICATE COMMAND NAMES ===")
for key, locations in sorted(cmd_locations.items()):
    if len(locations) > 1:
        print(f"DUPLICATE: '{key}'")
        for f, l in locations:
            print(f"  {f}:{l}")

print("\n=== ALL TOP-LEVEL COMMAND NAMES ===")
toplevel = {k: v for k, v in cmd_locations.items() if '/' not in k}
for name, locations in sorted(toplevel.items()):
    print(f"  {name}: {locations[0][0]}:{locations[0][1]}" + (f" (DUPLICATE! {len(locations)} defs)" if len(locations) > 1 else ""))