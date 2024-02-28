from pathlib import Path
from textwrap import dedent

from pytest import Pytester


def test_session_scoped_loop_configuration_works_in_auto_mode(
    pytester: Pytester,
):
    session_wide_mark_conftest = (
        Path(__file__).parent / "session_scoped_loop_example.py"
    )
    pytester.makeconftest(session_wide_mark_conftest.read_text())
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            session_loop = None

            async def test_store_loop(request):
                global session_loop
                session_loop = asyncio.get_running_loop()

            async def test_compare_loop(request):
                global session_loop
                assert asyncio.get_running_loop() is session_loop
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=auto")
    result.assert_outcomes(passed=2)


def test_session_scoped_loop_configuration_works_in_strict_mode(
    pytester: Pytester,
):
    session_wide_mark_conftest = (
        Path(__file__).parent / "session_scoped_loop_example.py"
    )
    pytester.makeconftest(session_wide_mark_conftest.read_text())
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            session_loop = None

            @pytest.mark.asyncio
            async def test_store_loop(request):
                global session_loop
                session_loop = asyncio.get_running_loop()

            @pytest.mark.asyncio
            async def test_compare_loop(request):
                global session_loop
                assert asyncio.get_running_loop() is session_loop
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)
