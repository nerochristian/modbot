import re

with open('database.py', encoding='utf-8') as f:
    content = f.read()

helper = '''

def _row_get(row: Any, column: str) -> Any:
    """Get a column value from a database row (dict or tuple).

    SQLite (aiosqlite) returns tuples, PostgreSQL (asyncpg via PostgresCompatCursor)
    returns dicts. This helper bridges both so call sites work either way.
    """
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(column)
    if isinstance(row, (tuple, list)):
        if len(row) == 1:
            return row[0]
        return row[0]
    try:
        return row[column]
    except (KeyError, IndexError, TypeError):
        try:
            return row[0]
        except (KeyError, IndexError, TypeError):
            return None


'''

# Insert helper before _parse_status_rowcount
content = content.replace(
    'def _parse_status_rowcount(status: str) -> int:',
    helper + 'def _parse_status_rowcount(status: str) -> int:'
)

# Fix all row[0] to _row_get(row, 'settings')
old = "json.loads(row[0]) if row and row[0] else {}"
new = "json.loads(_row_get(row, 'settings')) if row and _row_get(row, 'settings') else {}"
content = content.replace(old, new)

with open('database.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
count = content.count("_row_get(row, 'settings')")
print(f"Fixed {count} occurrences of row[0] -> _row_get(row, 'settings')")
print(f"Helper function added: {'_row_get' in content}")