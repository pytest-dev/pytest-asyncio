from textwrap import dedent

from pytest import Pytester


def test_asyncio_strict_mode_skip(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
                import pytest

                pytest_plugins = "pytest_asyncio"

                @pytest.mark.asyncio
                async def test_no_warning_on_skip():
                    pytest.skip("Test a skip error inside asyncio")
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(skipped=1)


def test_asyncio_auto_mode_skip(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
                import pytest

                pytest_plugins = "pytest_asyncio"

                async def test_no_warning_on_skip():
                    pytest.skip("Test a skip error inside asyncio")
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(skipped=1)


def test_asyncio_strict_mode_module_level_skip(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
                import pytest

                pytest.skip("Skip all tests", allow_module_level=True)

                @pytest.mark.asyncio
                async def test_is_skipped():
                    pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(skipped=1)


def test_asyncio_auto_mode_module_level_skip(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
                import pytest

                pytest.skip("Skip all tests", allow_module_level=True)

                async def test_is_skipped():
                    pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(skipped=1)


def test_asyncio_auto_mode_wrong_skip_usage(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
                import pytest

                pytest.skip("Skip all tests")

                async def test_is_skipped():
                    pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(errors=1)
