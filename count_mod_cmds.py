
import re

file_path = 'c:/Users/caleb/Downloads/modbot/modbot/cogs/moderation.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Count @mod_slash.command
matches = re.findall(r'@mod_slash\.command', content)
print(f"Direct subcommands: {len(matches)}")

# Count groups added
# self.mod_slash.add_command(self.whitelist_group)
# Check for .add_command
add_matches = re.findall(r'\.add_command\(', content)
print(f"Added commands/groups: {len(add_matches)}")
