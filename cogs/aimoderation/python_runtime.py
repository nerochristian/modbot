"""Validation and runtime helpers for owner-authorized AI Python actions."""
from __future__ import annotations

import ast
import builtins
import hashlib
from types import CodeType
from typing import Any, Dict


MAX_CODE_CHARS = 20_000
MAX_AST_NODES = 1_500
ALLOWED_IMPORTS = frozenset(
    {
        "asyncio",
        "collections",
        "csv",
        "datetime",
        "discord",
        "io",
        "itertools",
        "json",
        "math",
        "random",
        "re",
        "statistics",
        "time",
        "uuid",
    }
)
FORBIDDEN_NAMES = frozenset(
    {
        "breakpoint",
        "compile",
        "delattr",
        "eval",
        "exec",
        "globals",
        "input",
        "locals",
        "open",
        "vars",
        "__import__",
    }
)
FORBIDDEN_ATTRIBUTES = frozenset(
    {
        "close",
        "ensure_future",
        "http",
        "load_extension",
        "logout",
        "reload_extension",
        "run",
        "start",
        "token",
        "unload_extension",
    }
)


class PythonSafetyError(ValueError):
    """Raised when generated Python fails the owner-execution safety policy."""


def normalize_python_code(raw: str) -> str:
    code = str(raw or "").strip()
    for prefix in ("```python", "```py", "```"):
        if code.lower().startswith(prefix):
            code = code[len(prefix):]
            break
    if code.endswith("```"):
        code = code[:-3]
    return code.strip()


def wrap_async(code: str, function_name: str = "__ai_exec_func") -> str:
    indented = "\n".join(f"    {line}" for line in code.splitlines())
    return f"async def {function_name}():\n{indented}\n"


def execution_digest(code: str) -> str:
    return hashlib.sha256(normalize_python_code(code).encode("utf-8")).hexdigest()


def validate_python_code(code: str) -> CodeType:
    normalized = normalize_python_code(code)
    if not normalized:
        raise PythonSafetyError("No Python code was generated.")
    if len(normalized) > MAX_CODE_CHARS:
        raise PythonSafetyError(f"Generated code exceeds the {MAX_CODE_CHARS:,}-character limit.")

    wrapped = wrap_async(normalized)
    try:
        tree = ast.parse(wrapped, filename="<ai_exec>", mode="exec")
    except SyntaxError as exc:
        line = max(1, (exc.lineno or 2) - 1)
        raise PythonSafetyError(f"Syntax error on generated line {line}: {exc.msg}.") from exc

    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_AST_NODES:
        raise PythonSafetyError("Generated code is too complex to execute safely in one action.")

    for node in nodes:
        if isinstance(node, (ast.Global, ast.Nonlocal, ast.ClassDef)):
            raise PythonSafetyError(f"Generated code cannot use {type(node).__name__}.")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports = (
                [(node.module or "").split(".", 1)[0]]
                if isinstance(node, ast.ImportFrom)
                else [alias.name.split(".", 1)[0] for alias in node.names]
            )
            blocked = [name for name in imports if name not in ALLOWED_IMPORTS]
            if blocked:
                raise PythonSafetyError(f"Import `{blocked[0]}` is not available to generated actions.")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise PythonSafetyError(f"Generated code cannot use `{node.id}`.")
        if isinstance(node, ast.Attribute):
            attr = node.attr.lower()
            if attr.startswith("__") or attr in FORBIDDEN_ATTRIBUTES:
                raise PythonSafetyError(f"Generated code cannot access attribute `{node.attr}`.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"create_task", "ensure_future"}:
                raise PythonSafetyError("Generated code cannot start detached background tasks.")
            if node.func.attr == "threads":
                raise PythonSafetyError(
                    "Discord channel.threads is a list property; iterate it without calling or awaiting it."
                )
            if node.func.attr == "delete" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "guild":
                    raise PythonSafetyError("Generated code cannot delete the current server.")
        if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True:
            raise PythonSafetyError("Generated code cannot contain an unbounded `while True` loop.")

    try:
        return compile(tree, "<ai_exec>", "exec")
    except (SyntaxError, ValueError) as exc:
        raise PythonSafetyError(f"Generated code could not be compiled: {exc}.") from exc


def _safe_import(
    name: str,
    globals: Dict[str, Any] | None = None,
    locals: Dict[str, Any] | None = None,
    fromlist: tuple[str, ...] = (),
    level: int = 0,
) -> Any:
    root = name.split(".", 1)[0]
    if level or root not in ALLOWED_IMPORTS:
        raise ImportError(f"Import `{name}` is not available to generated actions.")
    return builtins.__import__(name, globals, locals, fromlist, level)


def _safe_setattr(obj: Any, name: str, value: Any) -> None:
    """Allow generated plans to toggle only documented Discord permission flags."""
    cls = type(obj)
    valid_flags = getattr(cls, "VALID_FLAGS", None)
    if (
        cls.__module__ != "discord.permissions"
        or cls.__name__ != "Permissions"
        or not isinstance(valid_flags, dict)
    ):
        raise TypeError("setattr is restricted to discord.Permissions instances.")
    if not isinstance(name, str) or name not in valid_flags or name.startswith("_"):
        raise AttributeError("Only documented Discord permission flags can be changed.")
    if not isinstance(value, bool):
        raise TypeError("Discord permission flags must be set with a boolean value.")
    builtins.setattr(obj, name, value)


def _safe_getattr(obj: Any, name: str, *default: Any) -> Any:
    """Expose public attributes without allowing dynamic access to blocked capabilities."""
    if not isinstance(name, str):
        raise TypeError("getattr attribute names must be strings.")
    normalized = name.lower()
    if name.startswith("_") or normalized in FORBIDDEN_ATTRIBUTES or normalized == "delete":
        raise AttributeError(f"Dynamic access to `{name}` is not available.")
    if len(default) > 1:
        raise TypeError("getattr accepts at most one default value.")
    if default:
        return builtins.getattr(obj, name, default[0])
    return builtins.getattr(obj, name)


def safe_builtins() -> Dict[str, Any]:
    names = (
        "ArithmeticError",
        "AssertionError",
        "AttributeError",
        "Exception",
        "KeyError",
        "LookupError",
        "RuntimeError",
        "StopAsyncIteration",
        "StopIteration",
        "TypeError",
        "ValueError",
        "ZeroDivisionError",
        "abs",
        "all",
        "any",
        "bool",
        "bytearray",
        "bytes",
        "callable",
        "chr",
        "dict",
        "divmod",
        "enumerate",
        "filter",
        "float",
        "format",
        "frozenset",
        "hash",
        "hasattr",
        "hex",
        "int",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "list",
        "map",
        "max",
        "min",
        "next",
        "object",
        "ord",
        "pow",
        "print",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "slice",
        "sorted",
        "str",
        "sum",
        "super",
        "tuple",
        "type",
        "zip",
    )
    allowed = {name: getattr(builtins, name) for name in names}
    allowed["__import__"] = _safe_import
    allowed["getattr"] = _safe_getattr
    allowed["setattr"] = _safe_setattr
    return allowed
