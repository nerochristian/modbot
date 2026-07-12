"""Lint guard: no bare `except:` in live bot code.

Bare excepts swallow asyncio.CancelledError and KeyboardInterrupt, which breaks
task cancellation and shutdown in an async bot. Phase 7 converted all of them to
`except Exception:`. This test keeps them from creeping back into the live tree.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIVE_DIRS = ["cogs", "utils", "db"]
BARE_EXCEPT = re.compile(r"^\s*except\s*:\s*(#.*)?$")


def _live_python_files():
    files = [ROOT / "bot.py"]
    for d in LIVE_DIRS:
        files.extend((ROOT / d).rglob("*.py"))
    # Skip anything under a scratch/dead directory if present.
    return [f for f in files if "ai_mod_temp" not in f.parts]


def test_no_bare_except_in_live_code():
    offenders = []
    for f in _live_python_files():
        for lineno, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if BARE_EXCEPT.match(line):
                offenders.append(f"{f.relative_to(ROOT)}:{lineno}")
    assert not offenders, "bare 'except:' found (use 'except Exception:'):\n" + "\n".join(offenders)
