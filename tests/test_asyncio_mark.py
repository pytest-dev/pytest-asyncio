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
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
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
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
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
    result = pytester.runpytest("--asyncio-mode=auto", "-W default")
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
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
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
    result = pytester.runpytest("--asyncio-mode=auto", "-W default")
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
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
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
    result = pytester.runpytest("--asyncio-mode=auto", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )
