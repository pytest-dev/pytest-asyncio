"""Pre-flight checks that run just before an asyncio test executes."""

from __future__ import annotations

import warnings

import pytest
from pytest import Function, PytestDeprecationWarning

from ._collection import _is_coroutine_or_asyncgen, is_async_test
from ._config import Mode, _get_asyncio_mode
from ._fixtures import _is_asyncio_fixture_function


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem: Function) -> object | None:
    """Pytest hook called before a test case is run."""
    if pyfuncitem.get_closest_marker("asyncio") is not None:
        if is_async_test(pyfuncitem):
            asyncio_mode = _get_asyncio_mode(pyfuncitem.config)
            for fixname, fixtures in pyfuncitem._fixtureinfo.name2fixturedefs.items():
                # name2fixturedefs is a dict between fixture name and a list of matching
                # fixturedefs. The last entry in the list is closest and the one used.
                func = fixtures[-1].func
                if (
                    asyncio_mode == Mode.STRICT
                    and _is_coroutine_or_asyncgen(func)
                    and not _is_asyncio_fixture_function(func)
                ):
                    warnings.warn(
                        PytestDeprecationWarning(
                            f"asyncio test {pyfuncitem.name!r} requested async "
                            "@pytest.fixture "
                            f"{fixname!r} in strict mode. "
                            "You might want to use @pytest_asyncio.fixture or switch "
                            "to auto mode. "
                            "This will become an error in future versions of "
                            "pytest-asyncio."
                        ),
                        stacklevel=1,
                    )
                    # no stacklevel points at the users code, so we set stacklevel=1
                    # so it at least indicates that it's the plugin complaining.
                    # Pytest gives the test file & name in the warnings summary at least

        else:
            pyfuncitem.warn(
                pytest.PytestWarning(
                    f"The test {pyfuncitem} is marked with '@pytest.mark.asyncio' "
                    "but it is not an async function. "
                    "Please remove the asyncio mark. "
                    "If the test is not marked explicitly, "
                    "check for global marks applied via 'pytestmark'."
                )
            )
    yield
    return None
