from textwrap import dedent

from pytest import Pytester


def test_import_warning_does_not_cause_internal_error(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
                raise ImportWarning()

                async def test_errors_out():
                    pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(errors=1)


def test_import_warning_in_package_does_not_cause_internal_error(pytester: Pytester):
    pytester.makepyfile(
        __init__=dedent(
            """\
                raise ImportWarning()
            """
        ),
        test_a=dedent(
            """\
                async def test_errors_out():
                    pass
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(errors=1)
