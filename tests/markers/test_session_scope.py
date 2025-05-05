from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_asyncio_mark_provides_session_scoped_loop_strict_mode(pytester: Pytester):
    package_name = pytester.path.name
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
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

            @pytest.mark.asyncio(loop_scope="session")
            async def test_remember_loop():
                shared_module.loop = asyncio.get_running_loop()
            """
        ),
        test_module_two=dedent(
            f"""\
            import asyncio
            import pytest

            from {package_name} import shared_module

            pytestmark = pytest.mark.asyncio(loop_scope="session")

            async def test_this_runs_in_same_loop():
                assert asyncio.get_running_loop() is shared_module.loop

            class TestClassA:
                async def test_this_runs_in_same_loop(self):
                    assert asyncio.get_running_loop() is shared_module.loop
            """
        ),
    )

    # subpackage_name must alphabetically come after test_module_one.py
    subpackage_name = "z_subpkg"
    subpkg = pytester.mkpydir(subpackage_name)
    subpkg.joinpath("test_subpkg.py").write_text(
        dedent(
            f"""\
            import asyncio
            import pytest

            from {package_name} import shared_module

            pytestmark = pytest.mark.asyncio(loop_scope="session")

            async def test_subpackage_runs_in_same_loop():
                assert asyncio.get_running_loop() is shared_module.loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=4)


def test_asyncio_mark_respects_the_loop_policy(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        __init__="",
        conftest=dedent(
            """\
            import pytest

            from .custom_policy import CustomEventLoopPolicy

            @pytest.fixture(scope="session")
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

            pytestmark = pytest.mark.asyncio(loop_scope="session")

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

            pytestmark = pytest.mark.asyncio(loop_scope="session")

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
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        __init__="",
        test_parametrization=dedent(
            """\
            import asyncio

            import pytest

            pytestmark = pytest.mark.asyncio(loop_scope="session")

            @pytest.fixture(
                scope="session",
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


def test_asyncio_mark_provides_session_scoped_loop_to_fixtures(
    pytester: Pytester,
):
    package_name = pytester.path.name
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        __init__="",
        conftest=dedent(
            f"""\
            import asyncio

            import pytest_asyncio

            from {package_name} import shared_module

            @pytest_asyncio.fixture(loop_scope="session", scope="session")
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
    )
    subpackage_name = "subpkg"
    subpkg = pytester.mkpydir(subpackage_name)
    subpkg.joinpath("test_subpkg.py").write_text(
        dedent(
            f"""\
            import asyncio

            import pytest
            import pytest_asyncio

            from {package_name} import shared_module

            pytestmark = pytest.mark.asyncio(loop_scope="session")

            async def test_runs_in_same_loop_as_fixture(my_fixture):
                assert asyncio.get_running_loop() is shared_module.loop
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_mark_allows_combining_session_scoped_fixture_with_package_scoped_test(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        __init__="",
        test_mixed_scopes=dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(loop_scope="session", scope="session")
            async def async_fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio(loop_scope="package")
            async def test_runs_in_different_loop_as_fixture(async_fixture):
                global loop
                assert asyncio.get_running_loop() is not loop
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_mark_allows_combining_session_scoped_fixture_with_module_scoped_test(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        __init__="",
        test_mixed_scopes=dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(loop_scope="session", scope="session")
            async def async_fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio(loop_scope="module")
            async def test_runs_in_different_loop_as_fixture(async_fixture):
                global loop
                assert asyncio.get_running_loop() is not loop
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_mark_allows_combining_session_scoped_fixture_with_class_scoped_test(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        __init__="",
        test_mixed_scopes=dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(loop_scope="session", scope="session")
            async def async_fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio(loop_scope="class")
            class TestMixedScopes:
                async def test_runs_in_different_loop_as_fixture(self, async_fixture):
                    global loop
                    assert asyncio.get_running_loop() is not loop
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_mark_allows_combining_session_scoped_fixture_with_function_scoped_test(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        __init__="",
        test_mixed_scopes=dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(loop_scope="session", scope="session")
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


def test_allows_combining_session_scoped_asyncgen_fixture_with_function_scoped_test(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        __init__="",
        test_mixed_scopes=dedent(
            """\
            import asyncio

            import pytest
            import pytest_asyncio

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(loop_scope="session", scope="session")
            async def async_fixture():
                global loop
                loop = asyncio.get_running_loop()
                yield

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
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import pytest
            import asyncio

            @pytest.fixture(scope="session")
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

            @pytest.mark.asyncio(loop_scope="session")
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
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.mark.asyncio(loop_scope="session")
            async def test_anything():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(warnings=0, passed=1)
