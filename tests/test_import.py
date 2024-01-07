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


def test_does_not_import_unrelated_packages(pytester: Pytester):
    pkg_dir = pytester.mkpydir("mypkg")
    pkg_dir.joinpath("__init__.py").write_text(
        dedent(
            """\
                raise ImportError()
            """
        ),
    )
    test_dir = pytester.mkdir("tests")
    test_dir.joinpath("test_a.py").write_text(
        dedent(
            """\
                async def test_passes():
                    pass
            """
        ),
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)
