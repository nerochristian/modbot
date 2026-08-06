import sys
sys.path.insert(0, ".")
from cogs import behavior_profiling as bp
print("import OK")
print("sections in empty:", bp._count_profile_sections(""))
