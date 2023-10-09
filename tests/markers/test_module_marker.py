from textwrap import dedent

from pytest import Pytester


def test_asyncio_mark_works_on_module_level(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest

            pytestmark = pytest.mark.asyncio


            class TestPyTestMark:
                async def test_is_asyncio(self, event_loop, sample_fixture):
                    assert asyncio.get_event_loop()

                    counter = 1

                    async def inc():
                        nonlocal counter
                        counter += 1
                        await asyncio.sleep(0)

                    await asyncio.ensure_future(inc())
                    assert counter == 2


            async def test_is_asyncio(event_loop, sample_fixture):
                assert asyncio.get_event_loop()
                counter = 1

                async def inc():
                    nonlocal counter
                    counter += 1
                    await asyncio.sleep(0)

                await asyncio.ensure_future(inc())
                assert counter == 2


            @pytest.fixture
            def sample_fixture():
                return None
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_mark_provides_module_scoped_loop_strict_mode(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytestmark = pytest.mark.asyncio_event_loop

            loop: asyncio.AbstractEventLoop

            @pytest.mark.asyncio
            async def test_remember_loop():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio
            async def test_this_runs_in_same_loop():
                global loop
                assert asyncio.get_running_loop() is loop

            class TestClassA:
                @pytest.mark.asyncio
                async def test_this_runs_in_same_loop(self):
                    global loop
                    assert asyncio.get_running_loop() is loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=3)


def test_asyncio_mark_provides_class_scoped_loop_auto_mode(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytestmark = pytest.mark.asyncio_event_loop

            loop: asyncio.AbstractEventLoop

            async def test_remember_loop():
                global loop
                loop = asyncio.get_running_loop()

            async def test_this_runs_in_same_loop():
                global loop
                assert asyncio.get_running_loop() is loop

            class TestClassA:
                async def test_this_runs_in_same_loop(self):
                    global loop
                    assert asyncio.get_running_loop() is loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=3)


def test_raise_when_event_loop_fixture_is_requested_in_addition_to_scoped_loop(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytestmark = pytest.mark.asyncio_event_loop

            @pytest.mark.asyncio
            async def test_remember_loop(event_loop):
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines("*MultipleEventLoopsRequestedError: *")


def test_asyncio_event_loop_mark_allows_specifying_the_loop_policy(
    pytester: Pytester,
):
    pytester.makepyfile(
        __init__="",
        custom_policy=dedent(
            """\
            import asyncio

            class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
                pass
            """
        ),
        test_uses_custom_policy=dedent(
            """\
            import asyncio
            import pytest

            from .custom_policy import CustomEventLoopPolicy

            pytestmark = pytest.mark.asyncio_event_loop(policy=CustomEventLoopPolicy())

            @pytest.mark.asyncio
            async def test_uses_custom_event_loop_policy():
                assert isinstance(
                    asyncio.get_event_loop_policy(),
                    CustomEventLoopPolicy,
                )
            """
        ),
        test_does_not_use_custom_policy=dedent(
            """\
            import asyncio
            import pytest

            from .custom_policy import CustomEventLoopPolicy

            @pytest.mark.asyncio
            async def test_does_not_use_custom_event_loop_policy():
                assert not isinstance(
                    asyncio.get_event_loop_policy(),
                   CustomEventLoopPolicy,
                )
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_event_loop_mark_allows_specifying_multiple_loop_policies(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest

            pytestmark = pytest.mark.asyncio_event_loop(
                policy=[
                    asyncio.DefaultEventLoopPolicy(),
                    asyncio.DefaultEventLoopPolicy(),
                ]
            )

            @pytest.mark.asyncio
            async def test_parametrized_loop():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_event_loop_mark_provides_module_scoped_loop_to_fixtures(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            pytestmark = pytest.mark.asyncio_event_loop

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture
            async def my_fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio
            async def test_runs_is_same_loop_as_fixture(my_fixture):
                global loop
                assert asyncio.get_running_loop() is loop
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)
