"""
Detects tests/fixtures whose effective loop_scope differs from a fixture
they (transitively) depend on -- i.e. a test or fixture that ends up running
on a different event loop than an async fixture it uses. See issue #1514."""

from __future__ import annotations

import pytest
from pytest import Config, Function

from ._config import _get_asyncio_mode
from ._fixtures import _effective_fixture_loop_scope, _owns_fixture
from ._hooks import _ScopeName


class PytestAsyncioLoopScopeMismatchWarning(pytest.PytestWarning):
    """
    Warns that a test or fixture requests an async fixture whose effective
    loop_scope differs from its own. The two will run on different event
    loops, which can silently break objects (e.g. asyncio.Future, Task, or
    Lock) that are bound to the loop they were created on.
    """


def _compute_loop_scope_mismatches(
    item: Function, test_loop_scope: _ScopeName, config: Config
) -> list[tuple[str, _ScopeName]]:
    """
    Walk the full transitive closure of `item`'s fixture dependencies and
    return (fixture_name, fixture_loop_scope) for every async-owned fixture
    whose effective loop_scope differs from `test_loop_scope`.

    `names_closure` is pytest's own deduplicated transitive closure (each
    fixture name appears at most once, however many paths reach it), so a
    single pass here can't produce duplicate entries for the same fixture
    even in a diamond-shaped dependency graph.
    """
    mode = _get_asyncio_mode(config)
    mismatches: list[tuple[str, _ScopeName]] = []
    for name in item._fixtureinfo.names_closure:
        fixturedefs = item._fixtureinfo.name2fixturedefs.get(name)
        if not fixturedefs:
            continue
        # The last entry is the closest/effective one, same convention used
        # elsewhere in the plugin (e.g. pytest_pyfunc_call's strict-mode
        # check).
        fixturedef = fixturedefs[-1]
        if not _owns_fixture(fixturedef.func, mode):
            continue
        fixture_loop_scope = _effective_fixture_loop_scope(
            fixturedef.func, fixturedef.scope, config
        )
        if fixture_loop_scope != test_loop_scope:
            mismatches.append((name, fixture_loop_scope))
    return mismatches
