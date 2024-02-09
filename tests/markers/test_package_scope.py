from textwrap import dedent

from pytest import Pytester


def test_asyncio_mark_provides_package_scoped_loop_strict_mode(pytester: Pytester):
    package_name = pytester.path.name
    subpackage_name = "subpkg"
    pytester.makepyfile(
        __init__="",
        shared_module=dedent(
            """\
            import asyncio

            loop: asyncio.AbstractEventLoop = None
            """
        ),
        test_module_one=dedent(
            f"""\
            import asyncio
            import pytest

            from {package_name} import shared_module

            @pytest.mark.asyncio(scope="package")
            async def test_remember_loop():
                shared_module.loop = asyncio.get_running_loop()
            """
        ),
        test_module_two=dedent(
            f"""\
            import asyncio
            import pytest

            from {package_name} import shared_module

            pytestmark = pytest.mark.asyncio(scope="package")

            async def test_this_runs_in_same_loop():
                assert asyncio.get_running_loop() is shared_module.loop

            class TestClassA:
                async def test_this_runs_in_same_loop(self):
                    assert asyncio.get_running_loop() is shared_module.loop
            """
        ),
    )
    subpkg = pytester.mkpydir(subpackage_name)
    subpkg.joinpath("__init__.py").touch()
    subpkg.joinpath("test_subpkg.py").write_text(
        dedent(
            f"""\
            import asyncio
            import pytest

            from {package_name} import shared_module

            pytestmark = pytest.mark.asyncio(scope="package")

            async def test_subpackage_runs_in_different_loop():
                assert asyncio.get_running_loop() is not shared_module.loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=4)


def test_raise_when_event_loop_fixture_is_requested_in_addition_to_scoped_loop(
    pytester: Pytester,
):
    pytester.makepyfile(
        __init__="",
        test_raises=dedent(
            """\
            import asyncio
            import pytest

            @pytest.mark.asyncio(scope="package")
            async def test_remember_loop(event_loop):
                pass
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines("*MultipleEventLoopsRequestedError: *")


def test_asyncio_mark_respects_the_loop_policy(
    pytester: Pytester,
):
    pytester.makepyfile(
        __init__="",
        conftest=dedent(
            """\
            import pytest

            from .custom_policy import CustomEventLoopPolicy

            @pytest.fixture(scope="package")
            def event_loop_policy():
                return CustomEventLoopPolicy()
            """
        ),
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

            pytestmark = pytest.mark.asyncio(scope="package")

            async def test_uses_custom_event_loop_policy():
                assert isinstance(
                    asyncio.get_event_loop_policy(),
                    CustomEventLoopPolicy,
                )
            """
        ),
        test_also_uses_custom_policy=dedent(
            """\
            import asyncio
            import pytest

            from .custom_policy import CustomEventLoopPolicy

            pytestmark = pytest.mark.asyncio(scope="package")

            async def test_also_uses_custom_event_loop_policy():
                assert isinstance(
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
        __init__="",
        test_parametrization=dedent(
            """\
            import asyncio

            import pytest

            pytestmark = pytest.mark.asyncio(scope="package")

            @pytest.fixture(
                scope="package",
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
        ),
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_mark_provides_package_scoped_loop_to_fixtures(
    pytester: Pytester,
):
    package_name = pytester.path.name
    pytester.makepyfile(
        __init__="",
        conftest=dedent(
            f"""\
            import asyncio

            import pytest_asyncio

            from {package_name} import shared_module

            @pytest_asyncio.fixture(scope="package")
            async def my_fixture():
                shared_module.loop = asyncio.get_running_loop()
            """
        ),
        shared_module=dedent(
            """\
            import asyncio

            loop: asyncio.AbstractEventLoop = None
            """
        ),
        test_fixture_runs_in_scoped_loop=dedent(
            f"""\
            import asyncio

            import pytest
            import pytest_asyncio

            from {package_name} import shared_module

            pytestmark = pytest.mark.asyncio(scope="package")

            async def test_runs_in_same_loop_as_fixture(my_fixture):
                assert asyncio.get_running_loop() is shared_module.loop
            """
        ),
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_mark_allows_combining_package_scoped_fixture_with_module_scoped_test(
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

            @pytest_asyncio.fixture(scope="package")
            async def async_fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio(scope="module")
            async def test_runs_in_different_loop_as_fixture(async_fixture):
                global loop
                assert asyncio.get_running_loop() is not loop
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_mark_allows_combining_package_scoped_fixture_with_class_scoped_test(
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

            @pytest_asyncio.fixture(scope="package")
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


def test_asyncio_mark_allows_combining_package_scoped_fixture_with_function_scoped_test(
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

            @pytest_asyncio.fixture(scope="package")
            async def async_fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio
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
        __init__="",
        test_loop_is_none=dedent(
            """\
            import pytest
            import asyncio

            @pytest.fixture(scope="package")
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

            @pytest.mark.asyncio(scope="package")
            # parametrization may impact fixture ordering
            @pytest.mark.parametrize("n", (0, 1))
            async def test_does_not_fail(sets_event_loop_to_none, n):
                pass
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_standalone_test_does_not_trigger_warning_about_no_current_event_loop_being_set(
    pytester: Pytester,
):
    pytester.makepyfile(
        __init__="",
        test_module=dedent(
            """\
            import pytest

            @pytest.mark.asyncio(scope="package")
            async def test_anything():
                pass
            """
        ),
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(warnings=0, passed=1)
