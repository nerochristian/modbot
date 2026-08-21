"""Make the project root importable and keep provider tests offline."""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture
def parser():
    """A bare instance of the routing/parsing mixin.

    The mixin is pure text logic, so it needs no bot, guild, or network.
    """
    from cogs.aimoderation.parsing import MessageParsingMixin

    class _Parser(MessageParsingMixin):
        pass

    return _Parser()


def pytest_addoption(parser):
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Also run tests that make real calls to configured AI vendors.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "live: makes real network calls to configured AI providers"
    )


def pytest_collection_modifyitems(config, items):
    """Keep vendor-dialling tests out of the default run.

    They cost tokens and fail on a flaky network, so they must be opt-in -- but
    they are the only tests that can notice an expired key, which is exactly
    how the moderation lane once broke while every unit test stayed green.
    """
    if config.getoption("--live"):
        return
    skip = pytest.mark.skip(reason="needs --live (makes real provider calls)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
