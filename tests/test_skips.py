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


def test_unittest_skiptest_compatibility(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
                from unittest import SkipTest

                raise SkipTest("Skip all tests")

                async def test_is_skipped():
                    pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(skipped=1)


def test_skip_in_module_does_not_skip_package(pytester: Pytester):
    pytester.makepyfile(
        __init__="",
        test_skip=dedent(
            """\
                import pytest

                pytest.skip("Skip all tests", allow_module_level=True)

                def test_a():
                    pass

                def test_b():
                    pass
            """
        ),
        test_something=dedent(
            """\
                import pytest

                @pytest.mark.asyncio
                async def test_something():
                    pass
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1, skipped=1)
