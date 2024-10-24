from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_asyncio_mark_provides_package_scoped_loop_strict_mode(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        __init__="",
        conftest=dedent(
            """\
            import pytest_asyncio
            @pytest_asyncio.fixture(loop_scope="module", scope="module")
            async def async_shared_module_fixture():
                return True
            """
        ),
        test_module_one=dedent(
            """\
            import pytest
            @pytest.mark.asyncio
            async def test_shared_module_fixture_use_a(async_shared_module_fixture):
                assert async_shared_module_fixture is True
            """
        ),
        test_module_two=dedent(
            """\
            import pytest
            @pytest.mark.asyncio
            async def test_shared_module_fixture_use_b(async_shared_module_fixture):
                assert async_shared_module_fixture is True
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)
