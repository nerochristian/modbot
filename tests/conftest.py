"""Test isolation: keep the real deployment environment out of the suite.

Importing almost any bot module transitively reaches ``config``, which calls
``load_dotenv(override=True)``. On a deployed machine that silently pulls the
live ``.env`` -- real base URLs and real API keys -- into the test process, so
results depended on which host you ran on.

That was not hypothetical. On the VPS, ``RELAYROUTER_BASE_URL`` points at
openrouter.ai, which flips ``_relayrouter_routes_to_openrouter()`` and changes
which credential the protected-task lane reads. Six tests failed there while
passing on the dev box, for no reason connected to the code under test.

We scrub provider configuration to fixed, obviously-fake values *before* any
test module is imported, so module-level constants are computed from a known
baseline. Tests that need a specific value still set it themselves via
``monkeypatch``/``patch.dict``, which continues to work unchanged.

Deliberately NOT cleared: ``DB_MODE``/``DATABASE_URL`` (tests set these
explicitly) and non-provider knobs, so this stays a minimal, targeted scrub.
"""
from __future__ import annotations

import os

# Anything that selects a provider, names a model, points at a gateway, or
# authenticates to one. Cleared so no live credential or endpoint leaks in.
_PROVIDER_ENV_PREFIXES = (
    "OPENROUTER_",
    "RELAYROUTER_",
    "AIMODEL_",
    "DEEPSEEK_",
    "DEEPSEA_",
    "DO_API_",
    "DO_INFERENCE_",
    "GALAXY_",
    "AI_MAX_TOKENS",
    "BRAVE_",
    "TAVILY_",
    "SERPAPI_",
)

# Pinned rather than deleted: these have host-dependent defaults, and a fixed
# fake value makes the baseline identical everywhere.
_PINNED_ENV = {
    "RELAYROUTER_BASE_URL": "https://relayrouter.test/v1",
    "OPENROUTER_BASE_URL": "https://openrouter.test/api/v1",
    "AIMODEL_BASE_URL": "https://aimodel.test/v1",
    "DEEPSEEK_BASE_URL": "https://deepseek.test/v1",
    "DO_INFERENCE_BASE_URL": "https://inference.test/v1",
}


def _scrub_provider_environment() -> None:
    for name in [
        key
        for key in os.environ
        if key.startswith(_PROVIDER_ENV_PREFIXES)
    ]:
        os.environ.pop(name, None)
    os.environ.update(_PINNED_ENV)


def _disable_dotenv_loading() -> None:
    """Stop ``load_dotenv(override=True)`` from re-importing the deployed .env.

    Scrubbing ``os.environ`` alone is not enough: ``config`` calls
    ``load_dotenv(override=True)`` at import time, which reads the real file
    and overwrites the scrub. Verified directly -- without this, the scrubbed
    ``RELAYROUTER_BASE_URL`` reverted to the live value on import.

    Patching the loader keeps the suite hermetic no matter which module
    imports ``config`` first, or how many times.
    """
    try:
        import dotenv
    except ModuleNotFoundError:  # dotenv absent: nothing can load a .env
        return

    def _noop_load_dotenv(*args, **kwargs) -> bool:
        return False

    dotenv.load_dotenv = _noop_load_dotenv
    # config.py does `from dotenv import load_dotenv`, binding its own
    # reference, so patch the module attribute before config is ever imported.
    dotenv.main.load_dotenv = _noop_load_dotenv  # type: ignore[attr-defined]


# Order matters: neutralize the loader first, then scrub, both at collection
# time -- before test modules import the provider constants.
_disable_dotenv_loading()
_scrub_provider_environment()
