from __future__ import annotations

from textwrap import dedent

import pytest
from pytest import Pytester


@pytest.mark.parametrize("test_loop_scope", ("function", "module", "session"))
def test_set_event_loop_none(pytester: Pytester, test_loop_scope: str):
    pytester.makeini(
        dedent(
            f"""\
            [pytest]
            asyncio_default_test_loop_scope = {test_loop_scope}
            asyncio_default_fixture_loop_scope = function
            """
        )
    )
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_before():
                pass


            def test_set_event_loop_none():
                asyncio.set_event_loop(None)


            @pytest.mark.asyncio
            async def test_after():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(passed=3)


def test_set_event_loop_none_class(pytester: Pytester):
    pytester.makeini(
        dedent(
            """\
            [pytest]
            asyncio_default_test_loop_scope = class
            asyncio_default_fixture_loop_scope = function
            """
        )
    )
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"


            class TestClass:
                @pytest.mark.asyncio
                async def test_before(self):
                    pass


                def test_set_event_loop_none(self):
                    asyncio.set_event_loop(None)


                @pytest.mark.asyncio
                async def test_after(self):
                    pass
            """
        )
    )
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(passed=3)
