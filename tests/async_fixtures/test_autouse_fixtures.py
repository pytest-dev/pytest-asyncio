from textwrap import dedent

import pytest
from pytest import Pytester


@pytest.mark.parametrize("autouse_fixture_scope", ("function", "module"))
def test_autouse_fixture_in_different_scope_triggers_multiple_event_loop_error(
    pytester: Pytester,
    autouse_fixture_scope: str,
):
    pytester.makepyfile(
        dedent(
            f"""\
            import asyncio
            import pytest
            import pytest_asyncio

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(autouse=True, scope="{autouse_fixture_scope}")
            async def autouse_fixture():
                pass

            @pytest_asyncio.fixture(scope="session")
            async def any_fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio(scope="session")
            async def test_runs_in_session_scoped_loop(any_fixture):
                global loop
                assert asyncio.get_running_loop() is loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines("*MultipleEventLoopsRequestedError: *")