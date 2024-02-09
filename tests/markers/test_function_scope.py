from textwrap import dedent

from pytest import Pytester


def test_asyncio_mark_provides_function_scoped_loop_strict_mode(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytestmark = pytest.mark.asyncio

            loop: asyncio.AbstractEventLoop

            async def test_remember_loop():
                global loop
                loop = asyncio.get_running_loop()

            async def test_does_not_run_in_same_loop():
                global loop
                assert asyncio.get_running_loop() is not loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_function_scope_supports_explicit_event_loop_fixture_request(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            pytestmark = pytest.mark.asyncio

            async def test_remember_loop(event_loop):
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=1, warnings=1)
    result.stdout.fnmatch_lines(
        '*is asynchronous and explicitly requests the "event_loop" fixture*'
    )


def test_asyncio_mark_respects_the_loop_policy(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytestmark = pytest.mark.asyncio

            class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
                pass

            @pytest.fixture(scope="function")
            def event_loop_policy():
                return CustomEventLoopPolicy()

            async def test_uses_custom_event_loop_policy():
                assert isinstance(
                    asyncio.get_event_loop_policy(),
                    CustomEventLoopPolicy,
                )
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_mark_respects_parametrized_loop_policies(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest

            pytestmark = pytest.mark.asyncio

            class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
                pass

            @pytest.fixture(
                scope="module",
                params=[
                    CustomEventLoopPolicy(),
                    CustomEventLoopPolicy(),
                ],
            )
            def event_loop_policy(request):
                return request.param

            async def test_parametrized_loop():
                assert isinstance(
                    asyncio.get_event_loop_policy(),
                    CustomEventLoopPolicy,
                )
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_mark_provides_function_scoped_loop_to_fixtures(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            pytestmark = pytest.mark.asyncio

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture
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


def test_asyncio_mark_handles_missing_event_loop_triggered_by_fixture(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest
            import asyncio

            @pytest.fixture
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

            @pytest.mark.asyncio
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

            @pytest.mark.asyncio
            async def test_anything():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(warnings=0, passed=1)
