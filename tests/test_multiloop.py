from textwrap import dedent

from pytest import Pytester


def test_event_loop_override(pytester: Pytester):
    pytester.makeconftest(
        dedent(
            '''\
            import asyncio

            import pytest


            @pytest.fixture
            def dependent_fixture(event_loop):
                """A fixture dependent on the event_loop fixture, doing some cleanup."""
                counter = 0

                async def just_a_sleep():
                    """Just sleep a little while."""
                    nonlocal event_loop
                    await asyncio.sleep(0.1)
                    nonlocal counter
                    counter += 1

                event_loop.run_until_complete(just_a_sleep())
                yield
                event_loop.run_until_complete(just_a_sleep())

                assert counter == 2


            class CustomSelectorLoop(asyncio.SelectorEventLoop):
                """A subclass with no overrides, just to test for presence."""


            @pytest.fixture
            def event_loop():
                """Create an instance of the default event loop for each test case."""
                loop = CustomSelectorLoop()
                yield loop
                loop.close()
            '''
        )
    )
    pytester.makepyfile(
        dedent(
            '''\
            """Unit tests for overriding the event loop."""
            import asyncio

            import pytest


            @pytest.mark.asyncio
            async def test_for_custom_loop():
                """This test should be executed using the custom loop."""
                await asyncio.sleep(0.01)
                assert type(asyncio.get_event_loop()).__name__ == "CustomSelectorLoop"


            @pytest.mark.asyncio
            async def test_dependent_fixture(dependent_fixture):
                await asyncio.sleep(0.1)
            '''
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=2, warnings=2)
