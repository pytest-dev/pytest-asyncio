from textwrap import dedent

from pytest import Pytester


def test_event_loop_fixture_finalizer_returns_fresh_loop_after_test(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest

            loop = asyncio.get_event_loop_policy().get_event_loop()

            @pytest.mark.asyncio
            async def test_1():
                # This async test runs in its own event loop
                global loop
                running_loop = asyncio.get_event_loop_policy().get_event_loop()
                # Make sure this test case received a different loop
                assert running_loop is not loop

            def test_2():
                # Code outside of pytest-asyncio should not receive a "used" event loop
                current_loop = asyncio.get_event_loop_policy().get_event_loop()
                assert not current_loop.is_running()
                assert not current_loop.is_closed()
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_event_loop_fixture_finalizer_can_handle_loop_set_to_none(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            def test_anything(event_loop):
                asyncio.get_event_loop_policy().set_event_loop(None)
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)
