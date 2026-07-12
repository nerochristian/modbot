"""Structural security regression tests for the moderation command suite.

These do not spin up Discord; they statically assert an invariant that is easy
to break by accident: every destructive action helper in ``management.py`` must
run the actor-authorization check (``can_moderate``) before acting.

Background: ``_unmute_logic`` and ``_unquarantine_logic`` (the "undo" pair) once
lacked this check, so any member could invoke the ``/unmute`` and ``/untimeout``
/ ``/unquarantine`` slash commands to reverse a moderator's action. The slash
commands are registered dynamically without decorators, so the ONLY actor gate
lives inside these ``_logic`` methods — if the call is missing, the command is
open to everyone. This test fails if that ever regresses.
"""

import ast
import pathlib

MANAGEMENT = (
    pathlib.Path(__file__).resolve().parent.parent
    / "cogs" / "moderation" / "extensions" / "management.py"
)

# Every helper here performs (or reverses) a moderation action on a member and
# is reachable from an undecorated slash command, so each MUST call
# ``can_moderate`` to authorize the invoking user.
DESTRUCTIVE_LOGIC_METHODS = {
    "_kick_logic",
    "_ban_logic",
    "_tempban_logic",
    "_softban_logic",
    "_mute_logic",
    "_unmute_logic",
    "_quarantine_logic",
    "_unquarantine_logic",
}


def _method_nodes():
    tree = ast.parse(MANAGEMENT.read_text(encoding="utf-8"))
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
    }


def _calls_can_moderate(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute) and sub.attr == "can_moderate":
            return True
    return False


def test_all_destructive_logic_methods_authorize_actor():
    methods = _method_nodes()
    missing_defs = DESTRUCTIVE_LOGIC_METHODS - methods.keys()
    assert not missing_defs, f"expected methods not found (renamed?): {missing_defs}"

    unguarded = {
        name
        for name in DESTRUCTIVE_LOGIC_METHODS
        if not _calls_can_moderate(methods[name])
    }
    assert not unguarded, (
        "these moderation helpers do not call can_moderate() and are reachable "
        f"from undecorated slash commands (permission hole): {sorted(unguarded)}"
    )
