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
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=2, warnings=2)
    result.stdout.fnmatch_lines(
        '*is asynchronous and explicitly requests the "event_loop" fixture*'
    )


def test_asyncio_mark_provides_module_scoped_loop_strict_mode(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytestmark = pytest.mark.asyncio(scope="module")

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
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=3)


def test_raise_when_event_loop_fixture_is_requested_in_addition_to_scoped_loop(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytestmark = pytest.mark.asyncio(scope="module")

            async def test_remember_loop(event_loop):
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines("*MultipleEventLoopsRequestedError: *")


def test_asyncio_mark_respects_the_loop_policy(
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

            pytestmark = pytest.mark.asyncio(scope="module")

            @pytest.fixture(scope="module")
            def event_loop_policy():
                return CustomEventLoopPolicy()

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

            pytestmark = pytest.mark.asyncio(scope="module")

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


def test_asyncio_mark_respects_parametrized_loop_policies(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest

            pytestmark = pytest.mark.asyncio(scope="module")

            @pytest.fixture(
                scope="module",
                params=[
                    asyncio.DefaultEventLoopPolicy(),
                    asyncio.DefaultEventLoopPolicy(),
                ],
            )
            def event_loop_policy(request):
                return request.param

            async def test_parametrized_loop():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_mark_provides_module_scoped_loop_to_fixtures(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            pytestmark = pytest.mark.asyncio(scope="module")

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(scope="module")
            async def my_fixture():
                global loop
                loop = asyncio.get_running_loop()

            async def test_runs_is_same_loop_as_fixture(my_fixture):
                global loop
                assert asyncio.get_running_loop() is loop
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_mark_allows_combining_module_scoped_fixture_with_class_scoped_test(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(scope="module")
            async def async_fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio(scope="class")
            class TestMixedScopes:
                async def test_runs_in_different_loop_as_fixture(self, async_fixture):
                    global loop
                    assert asyncio.get_running_loop() is not loop

            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_mark_allows_combining_module_scoped_fixture_with_function_scoped_test(
    pytester: Pytester,
):
    pytester.makepyfile(
        __init__="",
        test_mixed_scopes=dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(scope="module")
            async def async_fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio(scope="function")
            async def test_runs_in_different_loop_as_fixture(async_fixture):
                global loop
                assert asyncio.get_running_loop() is not loop
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_allows_combining_module_scoped_asyncgen_fixture_with_function_scoped_test(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(scope="module")
            async def async_fixture():
                global loop
                loop = asyncio.get_running_loop()
                yield

            @pytest.mark.asyncio(scope="function")
            async def test_runs_in_different_loop_as_fixture(async_fixture):
                global loop
                assert asyncio.get_running_loop() is not loop
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_mark_handles_missing_event_loop_triggered_by_fixture(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest
            import asyncio

            @pytest.fixture(scope="module")
            def sets_event_loop_to_none():
                # asyncio.run() creates a new event loop without closing the existing
                # one. For any test, but the first one, this leads to a ResourceWarning
                # when the discarded loop is destroyed by the garbage collector.
                # We close the current loop to avoid this
                try:
                    asyncio.get_event_loop().close()
                except RuntimeError:
                    pass
                return asyncio.run(asyncio.sleep(0))
                # asyncio.run() sets the current event loop to None when finished

            @pytest.mark.asyncio(scope="module")
            # parametrization may impact fixture ordering
            @pytest.mark.parametrize("n", (0, 1))
            async def test_does_not_fail(sets_event_loop_to_none, n):
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_standalone_test_does_not_trigger_warning_about_no_current_event_loop_being_set(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.mark.asyncio(scope="module")
            async def test_anything():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(warnings=0, passed=1)
