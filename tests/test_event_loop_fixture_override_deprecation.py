from textwrap import dedent

from pytest import Pytester


def test_emit_warning_when_event_loop_fixture_is_redefined(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.fixture
            def event_loop():
                loop = asyncio.new_event_loop()
                yield loop
                loop.close()

            @pytest.mark.asyncio
            async def test_emits_warning():
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*event_loop fixture provided by pytest-asyncio has been redefined*"]
    )


def test_emit_warning_when_event_loop_fixture_is_redefined_explicit_request(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.fixture
            def event_loop():
                loop = asyncio.new_event_loop()
                yield loop
                loop.close()

            @pytest.mark.asyncio
            async def test_emits_warning_when_requested_explicitly(event_loop):
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=1, warnings=2)
    result.stdout.fnmatch_lines(
        ["*event_loop fixture provided by pytest-asyncio has been redefined*"]
    )
    result.stdout.fnmatch_lines(
        ['*is asynchronous and explicitly requests the "event_loop" fixture*']
    )


def test_does_not_emit_warning_when_no_test_uses_the_event_loop_fixture(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.fixture
            def event_loop():
                loop = asyncio.new_event_loop()
                yield loop
                loop.close()

            def test_emits_no_warning():
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1, warnings=0)


def test_emit_warning_when_redefined_event_loop_is_used_by_fixture(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest
            import pytest_asyncio

            @pytest.fixture
            def event_loop():
                loop = asyncio.new_event_loop()
                yield loop
                loop.close()

            @pytest_asyncio.fixture
            async def uses_event_loop():
                pass

            def test_emits_warning(uses_event_loop):
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=1, warnings=1)
