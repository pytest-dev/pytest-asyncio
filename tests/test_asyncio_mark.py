from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_asyncio_mark_on_sync_function_emits_warning(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.mark.asyncio
            def test_a():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        ["*is marked with '@pytest.mark.asyncio' but it is not an async function.*"]
    )


def test_asyncio_mark_on_async_generator_function_emits_warning_in_strict_mode(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.mark.asyncio
            async def test_a():
                yield
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_function_emits_warning_in_auto_mode(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            async def test_a():
                yield
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=auto", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_method_emits_warning_in_strict_mode(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            class TestAsyncGenerator:
                @pytest.mark.asyncio
                async def test_a(self):
                    yield
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_method_emits_warning_in_auto_mode(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            class TestAsyncGenerator:
                @staticmethod
                async def test_a():
                    yield
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=auto", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_staticmethod_emits_warning_in_strict_mode(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            class TestAsyncGenerator:
                @staticmethod
                @pytest.mark.asyncio
                async def test_a():
                    yield
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_staticmethod_emits_warning_in_auto_mode(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            class TestAsyncGenerator:
                @staticmethod
                async def test_a():
                    yield
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=auto", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_marker_fallbacks_to_configured_default_loop_scope_if_not_set(
    pytester: Pytester,
):
    pytester.makeini(
        dedent(
            """\
            [pytest]
            asyncio_default_fixture_loop_scope = function
            asyncio_default_test_loop_scope = session
            """
        )
    )

    pytester.makepyfile(
        dedent(
            """\
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
            """
        )
    )

    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)


def test_asyncio_marker_uses_marker_loop_scope_even_if_config_is_set(
    pytester: Pytester,
):
    pytester.makeini(
        dedent(
            """\
            [pytest]
            asyncio_default_fixture_loop_scope = function
            asyncio_default_test_loop_scope = module
            """
        )
    )

    pytester.makepyfile(
        dedent(
            """\
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
            """
        )
    )

    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)
