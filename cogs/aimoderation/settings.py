"""Late-bound access to provider configuration.

Why this exists
---------------
Provider configuration lives as module-level constants in ``ai_client``
(``_OPENROUTER_API_KEY``, ``_RELAYROUTER_BASE_URL``, ...), computed from the
environment at import time. The test suite reconfigures them by patching that
module's namespace -- 83 sites across 17 names, e.g.::

    monkeypatch.setattr(ai_client_module, "_OPENROUTER_API_KEY", "test-key")
    patch("cogs.aimoderation.ai_client._DO_API_KEY", "key")

That works only while the *reader* resolves the name through the ``ai_client``
module object at call time. A module that does ``from .ai_client import
_OPENROUTER_API_KEY`` binds a snapshot instead, so the patch mutates a name
nobody reads: the provider silently keeps using the real environment value.
Demonstrated directly::

    stays in ai_client  -> PATCHED-BY-TEST
    moved to providers/ -> real-empty      # patch had no effect

The dangerous half is not the tests that fail -- it is the ones that keep
passing while exercising live credentials and asserting nothing.

The contract
------------
Any code outside ``ai_client`` that needs provider configuration MUST go
through :func:`setting` (or :func:`call`), never a ``from``-import. This
resolves the attribute on the ``ai_client`` module at call time, so patches
apply and extracted provider modules stay testable.

``ai_client`` imports this module, and this module reaches back into
``ai_client`` lazily, so there is no import cycle: the lookup happens after
both modules finish importing.
"""
from __future__ import annotations

import sys
from typing import Any

_AI_CLIENT_MODULE = "cogs.aimoderation.ai_client"

_MISSING = object()


def _ai_client_module() -> Any:
    """Return the live ``ai_client`` module object.

    Read out of ``sys.modules`` rather than kept in a global, so the value is
    never a stale snapshot and importing this module cannot trigger a cycle.
    """
    module = sys.modules.get(_AI_CLIENT_MODULE)
    if module is None:  # pragma: no cover - only on direct standalone import
        import importlib

        module = importlib.import_module(_AI_CLIENT_MODULE)
    return module


def setting(name: str, default: Any = _MISSING) -> Any:
    """Read provider configuration late-bound, honoring test patches.

    Use this instead of importing the constant::

        # WRONG - snapshots the value, patches silently do nothing:
        from .ai_client import _OPENROUTER_API_KEY

        # RIGHT - resolved at call time:
        settings.setting("_OPENROUTER_API_KEY")
    """
    module = _ai_client_module()
    if default is _MISSING:
        return getattr(module, name)
    return getattr(module, name, default)


def call(name: str, *args: Any, **kwargs: Any) -> Any:
    """Invoke a late-bound predicate such as ``_openrouter_conversation_enabled``.

    Needed because tests also patch the enablement helpers themselves
    (e.g. ``patch("...ai_client._deepseek_api_enabled", return_value=False)``),
    so the function object must be looked up at call time too.
    """
    return getattr(_ai_client_module(), name)(*args, **kwargs)
