from textwrap import dedent

from pytest import Pytester


def test_asyncio_marker_compatibility_with_skip(pytester: Pytester):
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


def test_asyncio_auto_mode_compatibility_with_skip(pytester: Pytester):
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
