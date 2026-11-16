from __future__ import annotations

from typing import Any

import pytest

import pytest_asyncio


@pytest.mark.parametrize("loop_scope", ["modul", "fixture", "", 42])
@pytest.mark.parametrize("use_factory", [False, True])
def test_invalid_fixture_loop_scope_is_rejected(
    loop_scope: Any, use_factory: bool
) -> None:
    async def example_fixture() -> int:
        return 1

    with pytest.raises(pytest.UsageError) as caught:
        if use_factory:
            pytest_asyncio.fixture(loop_scope=loop_scope)(example_fixture)
        else:
            pytest_asyncio.fixture(example_fixture, loop_scope=loop_scope)

    message = str(caught.value)
    assert repr(loop_scope) in message
    assert "loop_scope" in message
    for valid_scope in ("function", "class", "module", "package", "session"):
        assert valid_scope in message
