from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_asyncio_mark_on_sync_function_emits_warning(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            import pytest

            @pytest.mark.asyncio
            def test_a():
                pass
            """))
    result = pytester.runpytest("--asyncio-mode=strict", "-W default", "--assert=plain")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        ["*is marked with '@pytest.mark.asyncio' but it is not an async function.*"]
    )


def test_asyncio_mark_on_async_generator_function_emits_warning_in_strict_mode(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            import pytest

            @pytest.mark.asyncio
            async def test_a():
                yield
            """))
    result = pytester.runpytest("--asyncio-mode=strict", "-W default", "--assert=plain")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_function_emits_warning_in_auto_mode(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            async def test_a():
                yield
            """))
    result = pytester.runpytest("--asyncio-mode=auto", "-W default", "--assert=plain")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_method_emits_warning_in_strict_mode(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            import pytest

            class TestAsyncGenerator:
                @pytest.mark.asyncio
                async def test_a(self):
                    yield
            """))
    result = pytester.runpytest("--asyncio-mode=strict", "-W default", "--assert=plain")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_method_emits_warning_in_auto_mode(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            class TestAsyncGenerator:
                @staticmethod
                async def test_a():
                    yield
            """))
    result = pytester.runpytest("--asyncio-mode=auto", "-W default", "--assert=plain")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_staticmethod_emits_warning_in_strict_mode(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            import pytest

            class TestAsyncGenerator:
                @staticmethod
                @pytest.mark.asyncio
                async def test_a():
                    yield
            """))
    result = pytester.runpytest("--asyncio-mode=strict", "-W default", "--assert=plain")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_staticmethod_emits_warning_in_auto_mode(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            class TestAsyncGenerator:
                @staticmethod
                async def test_a():
                    yield
            """))
    result = pytester.runpytest("--asyncio-mode=auto", "-W default", "--assert=plain")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_marker_fallbacks_to_configured_default_loop_scope_if_not_set(
    pytester: Pytester,
):
    pytester.makeini(dedent("""\
            [pytest]
            asyncio_default_fixture_loop_scope = function
            asyncio_default_test_loop_scope = session
            """))

    pytester.makepyfile(dedent("""\
            import asyncio
            import pytest_asyncio
            import pytest

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(loop_scope="session", scope="session")
            async def session_loop_fixture():
                global loop
                loop = asyncio.get_running_loop()

            async def test_a(session_loop_fixture):
                global loop
                assert asyncio.get_running_loop() is loop
            """))

    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)


def test_asyncio_marker_uses_marker_loop_scope_even_if_config_is_set(
    pytester: Pytester,
):
    pytester.makeini(dedent("""\
            [pytest]
            asyncio_default_fixture_loop_scope = function
            asyncio_default_test_loop_scope = module
            """))

    pytester.makepyfile(dedent("""\
            import asyncio
            import pytest_asyncio
            import pytest

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(loop_scope="session", scope="session")
            async def session_loop_fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio(loop_scope="session")
            async def test_a(session_loop_fixture):
                global loop
                assert asyncio.get_running_loop() is loop
            """))

    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)


def test_asyncio_marker_applied_in_pycollect_makeitem_runs_in_strict_mode(
    pytester: Pytester,
):
    """
    Applying the asyncio marker in pytest_pycollect_makeitem, before
    pytest-asyncio's collection-time conversion runs, produces a working
    asyncio test (see issue #810)."""
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
            import inspect

            import pytest


            def pytest_pycollect_makeitem(collector, name, obj):
                if inspect.iscoroutinefunction(obj) and name.startswith("test"):
                    pytest.mark.asyncio(obj)
                return None
            """))
    pytester.makepyfile(dedent("""\
            import pytest


            @pytest.mark.asyncio
            async def test_a():
                assert True
            """))
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=1, warnings=0)


def test_asyncio_marker_applied_after_collection_emits_actionable_warning(
    pytester: Pytester,
):
    """
    A marker applied via pytest_collection_modifyitems arrives after the
    collection-time conversion, so the warning must point to the supported
    pytest_pycollect_makeitem path instead of telling the user to remove the
    marker (see issue #810)."""
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
            import inspect

            import pytest


            def pytest_collection_modifyitems(config, items):
                for item in items:
                    function = getattr(item, "function", None)
                    if function is not None and inspect.iscoroutinefunction(function):
                        item.add_marker(pytest.mark.asyncio)
            """))
    pytester.makepyfile(dedent("""\
            async def test_a():
                assert True
            """))
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=0, failed=1)
    result.stdout.fnmatch_lines(
        ["*is marked with '@pytest.mark.asyncio', but the marker was applied*"]
    )
    result.stdout.fnmatch_lines(["*pytest_pycollect_makeitem*"])
