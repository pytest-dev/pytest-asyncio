from textwrap import dedent

from pytest import Pytester


def test_emit_warning_when_event_loop_is_explicitly_requested_in_coroutine(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.mark.asyncio
            async def test_coroutine_emits_warning(event_loop):
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ['*is asynchronous and explicitly requests the "event_loop" fixture*']
    )


def test_emit_warning_when_event_loop_is_explicitly_requested_in_coroutine_method(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            class TestEmitsWarning:
                @pytest.mark.asyncio
                async def test_coroutine_emits_warning(self, event_loop):
                    pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ['*is asynchronous and explicitly requests the "event_loop" fixture*']
    )


def test_emit_warning_when_event_loop_is_explicitly_requested_in_coroutine_staticmethod(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            class TestEmitsWarning:
                @staticmethod
                @pytest.mark.asyncio
                async def test_coroutine_emits_warning(event_loop):
                    pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ['*is asynchronous and explicitly requests the "event_loop" fixture*']
    )


def test_emit_warning_when_event_loop_is_explicitly_requested_in_coroutine_fixture(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest
            import pytest_asyncio

            @pytest_asyncio.fixture
            async def emits_warning(event_loop):
                pass

            @pytest.mark.asyncio
            async def test_uses_fixture(emits_warning):
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ['*is asynchronous and explicitly requests the "event_loop" fixture*']
    )


def test_emit_warning_when_event_loop_is_explicitly_requested_in_async_gen_fixture(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest
            import pytest_asyncio

            @pytest_asyncio.fixture
            async def emits_warning(event_loop):
                yield

            @pytest.mark.asyncio
            async def test_uses_fixture(emits_warning):
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ['*is asynchronous and explicitly requests the "event_loop" fixture*']
    )


def test_does_not_emit_warning_when_event_loop_is_explicitly_requested_in_sync_function(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            def test_uses_fixture(event_loop):
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_does_not_emit_warning_when_event_loop_is_explicitly_requested_in_sync_fixture(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.fixture
            def any_fixture(event_loop):
                pass

            def test_uses_fixture(any_fixture):
                pass
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)
