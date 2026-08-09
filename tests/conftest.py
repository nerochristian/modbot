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
    # config.load_dotenv(override=True) would otherwise re-import the live file
    # the moment some module touches config. Point it at a path that cannot
    # exist so the scrub survives.
    os.environ.setdefault("DOTENV_PATH", "")


# Runs at collection time, before test modules (and therefore before the
# module-level provider constants) are imported.
_scrub_provider_environment()
