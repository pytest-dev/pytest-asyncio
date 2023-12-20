from textwrap import dedent

from pytest import Pytester


def test_import_warning(pytester: Pytester):
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
