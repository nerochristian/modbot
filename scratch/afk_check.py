import ast
import sys

src = open("cogs/utility.py", encoding="utf-8").read()
tree = ast.parse(src)
wanted = {"strip_afk_prefix", "build_afk_nick"}
from typing import Optional

ns = {"Optional": Optional}
mod = ast.Module(
    body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    + [n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") in {"AFK_NICK_PREFIX", "NICK_MAX_LENGTH"}],
    type_ignores=[],
)
mod.body.sort(key=lambda n: n.lineno)
exec(compile(ast.fix_missing_locations(mod), "<afk>", "exec"), ns)

strip_afk_prefix = ns["strip_afk_prefix"]
build_afk_nick = ns["build_afk_nick"]

cases = [
    "[AFK] [AFK] Cherry's Wife",
    "Cherry's Wife",
    "[afk] [AFK]  Bob",
    "[AFK] Bob",
    "X" * 40,
    "",
    None,
]
for c in cases:
    nick = build_afk_nick(c)
    print(repr(c), "->", repr(nick), "len", len(nick))
    assert len(nick) <= 32, "nick too long"
    assert build_afk_nick(nick) == nick, "not idempotent (prefix stacks)"
    assert not strip_afk_prefix(nick).upper().startswith("[AFK]"), "prefix stacked"

assert strip_afk_prefix("[AFK] [AFK] Bob") == "Bob"
assert strip_afk_prefix("Bob") == "Bob"
assert strip_afk_prefix(None) == ""
print("ALL_OK")
