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
