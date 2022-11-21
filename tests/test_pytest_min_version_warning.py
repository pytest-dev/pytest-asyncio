from textwrap import dedent

import pytest


@pytest.mark.skipif(
    pytest.__version__ < "7.0.0",
    reason="The warning shouldn't be present when run with recent pytest versions",
)
@pytest.mark.parametrize("mode", ("auto", "strict"))
def test_pytest_min_version_warning_is_not_triggered_for_pytest_7(testdir, mode):
    testdir.makepyfile(
        dedent(
            """\
            import pytest

            pytest_plugins = 'pytest_asyncio'

            @pytest.mark.asyncio
            async def test_triggers_pytest_warning():
                pass
            """
        )
    )
    result = testdir.runpytest(f"--asyncio-mode={mode}")
    result.assert_outcomes(passed=1, warnings=0)
