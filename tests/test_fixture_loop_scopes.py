from textwrap import dedent

import pytest
from pytest import Pytester


@pytest.mark.parametrize(
    "fixture_scope", ("session", "package", "module", "class", "function")
)
def test_loop_scope_session_is_independent_of_fixture_scope(
    pytester: Pytester,
    fixture_scope: str,
):
    pytester.makepyfile(
        dedent(
            f"""\
            import asyncio
            import pytest
            import pytest_asyncio

            loop: asyncio.AbstractEventLoop = None

            @pytest_asyncio.fixture(scope="{fixture_scope}", loop_scope="session")
            async def fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio(scope="session")
            async def test_runs_in_same_loop_as_fixture(fixture):
                global loop
                assert loop == asyncio.get_running_loop()
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)
