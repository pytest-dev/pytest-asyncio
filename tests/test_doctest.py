from textwrap import dedent

from pytest import Pytester


def test_plugin_does_not_interfere_with_doctest_collection(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            '''\
            def any_function():
                """
                >>> 42
                42
                """
            '''
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict", "--doctest-modules")
    result.assert_outcomes(passed=1)


def test_plugin_does_not_interfere_with_doctest_textfile_collection(pytester: Pytester):
    pytester.makefile(".txt", "")  # collected as DoctestTextfile
    pytester.makepyfile(
        __init__="",
        test_python_file=dedent(
            """\
                import pytest

                pytest_plugins = "pytest_asyncio"

                @pytest.mark.asyncio
                async def test_anything():
                    pass
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)
