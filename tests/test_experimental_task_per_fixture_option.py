"""The asyncio_experimental_task_per_fixture configuration option."""

from __future__ import annotations

import sys
from textwrap import dedent

import pytest
from pytest import Config, MonkeyPatch, Pytester


@pytest.mark.parametrize(
    ("setting", "same_task"),
    [
        pytest.param("", "False", id="unset"),
        pytest.param(
            "asyncio_experimental_task_per_fixture = false", "False", id="false"
        ),
        pytest.param(
            "asyncio_experimental_task_per_fixture = true",
            "True",
            id="true",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 11),
                reason="asyncio_experimental_task_per_fixture requires Python 3.11",
            ),
        ),
    ],
)
def test_only_the_enabled_option_tears_down_a_fixture_in_its_setup_task(
    pytester: Pytester, monkeypatch: MonkeyPatch, setting: str, same_task: str
):
    # The runner selected for this session would override the setting
    # under test.
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    pytester.makeini(
        f"[pytest]\nasyncio_default_fixture_loop_scope = function\n{setting}"
    )
    pytester.makepyfile(dedent("""\
        import asyncio
        from pathlib import Path

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def resource():
            setup_task = asyncio.current_task()
            yield
            same_task = asyncio.current_task() is setup_task
            Path("same-task.txt").write_text(str(same_task))

        @pytest.mark.asyncio
        async def test_uses_resource(resource):
            pass
        """))

    result = pytester.runpytest("--asyncio-mode=strict")

    result.assert_outcomes(passed=1)
    assert (pytester.path / "same-task.txt").read_text() == same_task


@pytest.mark.skipif(
    sys.version_info >= (3, 11), reason="Python 3.11 supports the option"
)
def test_enabling_the_option_on_python_3_10_is_a_usage_error(pytester: Pytester):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )

    result = pytester.runpytest()

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(
        ["*asyncio_experimental_task_per_fixture requires Python 3.11*"]
    )


def test_pytester_sessions_use_the_option_of_this_session(
    pytester: Pytester, pytestconfig: Config
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile("def test_passes(): pass")

    result = pytester.runpytest()

    reports_the_option = (
        "asyncio_experimental_task_per_fixture=True" in result.stdout.str()
    )
    assert reports_the_option is pytestconfig.getini(
        "asyncio_experimental_task_per_fixture"
    )
