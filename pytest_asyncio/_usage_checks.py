"""Collection-time usage checks: fail fast on removed public API."""

from __future__ import annotations

import pytest

_EVENT_LOOP_POLICY_FIXTURE_REMOVED_MESSAGE = """\
The "event_loop_policy" fixture was removed in pytest-asyncio 2.0. Defining \
a fixture with this name no longer has any effect on event loop creation. \
Use the "pytest_asyncio_loop_factories" hook to customize event loop \
creation instead. See the migration guide: \
https://pytest-asyncio.readthedocs.io/en/stable/how-to-guides/migrate_from_1_x.html\
"""


@pytest.hookimpl
def pytest_collection_finish(session: pytest.Session) -> None:
    fixturedefs = session._fixturemanager._arg2fixturedefs.get("event_loop_policy", ())
    if fixturedefs:
        raise pytest.UsageError(_EVENT_LOOP_POLICY_FIXTURE_REMOVED_MESSAGE)
