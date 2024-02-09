"""Test if pytestmark works when defined on a class."""

import asyncio
from textwrap import dedent

import pytest


class TestPyTestMark:
    pytestmark = pytest.mark.asyncio

    async def test_is_asyncio(self, sample_fixture):
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


def test_asyncio_mark_provides_class_scoped_loop_when_applied_to_functions(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            class TestClassScopedLoop:
                loop: asyncio.AbstractEventLoop

                @pytest.mark.asyncio(scope="class")
                async def test_remember_loop(self):
                    TestClassScopedLoop.loop = asyncio.get_running_loop()

                @pytest.mark.asyncio(scope="class")
                async def test_this_runs_in_same_loop(self):
                    assert asyncio.get_running_loop() is TestClassScopedLoop.loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_mark_provides_class_scoped_loop_when_applied_to_class(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.mark.asyncio(scope="class")
            class TestClassScopedLoop:
                loop: asyncio.AbstractEventLoop

                async def test_remember_loop(self):
                    TestClassScopedLoop.loop = asyncio.get_running_loop()

                async def test_this_runs_in_same_loop(self):
                    assert asyncio.get_running_loop() is TestClassScopedLoop.loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_mark_raises_when_class_scoped_is_request_without_class(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.mark.asyncio(scope="class")
            async def test_has_no_surrounding_class():
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        "*is marked to be run in an event loop with scope*",
    )


def test_asyncio_mark_is_inherited_to_subclasses(pytester: pytest.Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.mark.asyncio(scope="class")
            class TestSuperClassWithMark:
                pass

            class TestWithoutMark(TestSuperClassWithMark):
                loop: asyncio.AbstractEventLoop

                async def test_remember_loop(self):
                    TestWithoutMark.loop = asyncio.get_running_loop()

                async def test_this_runs_in_same_loop(self):
                    assert asyncio.get_running_loop() is TestWithoutMark.loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_mark_respects_the_loop_policy(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
                pass

            class TestUsesCustomEventLoop:
                @pytest.fixture(scope="class")
                def event_loop_policy(self):
                    return CustomEventLoopPolicy()

                @pytest.mark.asyncio
                async def test_uses_custom_event_loop_policy(self):
                    assert isinstance(
                        asyncio.get_event_loop_policy(),
                        CustomEventLoopPolicy,
                    )

            @pytest.mark.asyncio
            async def test_does_not_use_custom_event_loop_policy():
                assert not isinstance(
                    asyncio.get_event_loop_policy(),
                    CustomEventLoopPolicy,
                )
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_mark_respects_parametrized_loop_policies(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest

            @pytest.fixture(
                scope="class",
                params=[
                    asyncio.DefaultEventLoopPolicy(),
                    asyncio.DefaultEventLoopPolicy(),
                ]
            )
            def event_loop_policy(request):
                return request.param

            @pytest.mark.asyncio(scope="class")
            class TestWithDifferentLoopPolicies:
                async def test_parametrized_loop(self, request):
                    pass
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_mark_provides_class_scoped_loop_to_fixtures(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            @pytest.mark.asyncio(scope="class")
            class TestClassScopedLoop:
                loop: asyncio.AbstractEventLoop

                @pytest_asyncio.fixture
                async def my_fixture(self):
                    TestClassScopedLoop.loop = asyncio.get_running_loop()

                @pytest.mark.asyncio
                async def test_runs_is_same_loop_as_fixture(self, my_fixture):
                    assert asyncio.get_running_loop() is TestClassScopedLoop.loop
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_mark_allows_combining_class_scoped_fixture_with_function_scoped_test(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            loop: asyncio.AbstractEventLoop

            class TestMixedScopes:
                @pytest_asyncio.fixture(scope="class")
                async def async_fixture(self):
                    global loop
                    loop = asyncio.get_running_loop()

                @pytest.mark.asyncio(scope="function")
                async def test_runs_in_different_loop_as_fixture(self, async_fixture):
                    global loop
                    assert asyncio.get_running_loop() is not loop

            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_mark_handles_missing_event_loop_triggered_by_fixture(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest
            import asyncio

            class TestClass:
                @pytest.fixture(scope="class")
                def sets_event_loop_to_none(self):
                    # asyncio.run() creates a new event loop without closing the
                    # existing one. For any test, but the first one, this leads to
                    # a ResourceWarning when the discarded loop is destroyed by the
                    # garbage collector. We close the current loop to avoid this.
                    try:
                        asyncio.get_event_loop().close()
                    except RuntimeError:
                        pass
                    return asyncio.run(asyncio.sleep(0))
                    # asyncio.run() sets the current event loop to None when finished

                @pytest.mark.asyncio(scope="class")
                # parametrization may impact fixture ordering
                @pytest.mark.parametrize("n", (0, 1))
                async def test_does_not_fail(self, sets_event_loop_to_none, n):
                    pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_standalone_test_does_not_trigger_warning_about_no_current_event_loop_being_set(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.mark.asyncio(scope="class")
            class TestClass:
                async def test_anything(self):
                    pass
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(warnings=0, passed=1)
