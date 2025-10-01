from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_asyncio_mark_on_sync_function_emits_warning(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.mark.asyncio
            def test_a():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        ["*is marked with '@pytest.mark.asyncio' but it is not an async function.*"]
    )


def test_asyncio_mark_on_async_generator_function_emits_warning_in_strict_mode(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.mark.asyncio
            async def test_a():
                yield
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_function_emits_warning_in_auto_mode(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            async def test_a():
                yield
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=auto", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_method_emits_warning_in_strict_mode(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            class TestAsyncGenerator:
                @pytest.mark.asyncio
                async def test_a(self):
                    yield
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_method_emits_warning_in_auto_mode(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            class TestAsyncGenerator:
                @staticmethod
                async def test_a():
                    yield
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=auto", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_staticmethod_emits_warning_in_strict_mode(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            class TestAsyncGenerator:
                @staticmethod
                @pytest.mark.asyncio
                async def test_a():
                    yield
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_mark_on_async_generator_staticmethod_emits_warning_in_auto_mode(
    pytester: Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            class TestAsyncGenerator:
                @staticmethod
                async def test_a():
                    yield
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=auto", "-W default")
    result.assert_outcomes(xfailed=1, warnings=1)
    result.stdout.fnmatch_lines(
        ["*Tests based on asynchronous generators are not supported*"]
    )


def test_asyncio_marker_uses_marker_loop_scope_even_if_config_is_set(
    pytester: Pytester,
):
    pytester.makeini(
        dedent(
            """\
            [pytest]
            asyncio_default_fixture_loop_scope = function
            asyncio_default_test_loop_scope = module
            """
        )
    )

    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest_asyncio
            import pytest

            loop: asyncio.AbstractEventLoop

            @pytest_asyncio.fixture(loop_scope="session", scope="session")
            async def session_loop_fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio(loop_scope="session")
            async def test_a(session_loop_fixture):
                global loop
                assert asyncio.get_running_loop() is loop
            """
        )
    )

    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)


def test_uses_loop_factory_from_test(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest_asyncio
            import pytest

            class CustomEventLoop(asyncio.SelectorEventLoop):
                pass

            @pytest_asyncio.fixture(loop_scope="module")
            async def any_fixture():
                assert type(asyncio.get_running_loop()) == CustomEventLoop

            @pytest.mark.asyncio(loop_scope="module", loop_factory=CustomEventLoop)
            async def test_set_loop_factory(any_fixture):
                assert type(asyncio.get_running_loop()) == CustomEventLoop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_uses_loop_factory_from_fixture(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest_asyncio
            import pytest

            class CustomEventLoop(asyncio.SelectorEventLoop):
                pass

            @pytest_asyncio.fixture(loop_scope="module", loop_factory=CustomEventLoop)
            async def any_fixture():
                assert type(asyncio.get_running_loop()) == CustomEventLoop

            @pytest.mark.asyncio(loop_scope="module")
            async def test_set_loop_factory(any_fixture):
                assert type(asyncio.get_running_loop()) == CustomEventLoop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_uses_loop_factory_from_transitive_fixture(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest_asyncio
            import pytest

            class CustomEventLoop(asyncio.SelectorEventLoop):
                pass

            @pytest_asyncio.fixture(loop_scope="module", loop_factory=CustomEventLoop)
            async def transitive_fixture():
                assert type(asyncio.get_running_loop()) == CustomEventLoop

            @pytest_asyncio.fixture(loop_scope="module")
            async def any_fixture(transitive_fixture):
                assert type(asyncio.get_running_loop()) == CustomEventLoop

            @pytest.mark.asyncio(loop_scope="module")
            async def test_set_loop_factory(any_fixture):
                assert type(asyncio.get_running_loop()) == CustomEventLoop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_conflicting_loop_factories_in_tests_raise_error(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest_asyncio
            import pytest

            class CustomEventLoop(asyncio.SelectorEventLoop):
                pass

            class AnotherCustomEventLoop(asyncio.SelectorEventLoop):
                pass

            @pytest.mark.asyncio(loop_scope="module", loop_factory=CustomEventLoop)
            async def test_with_custom_loop_factory():
                ...

            @pytest.mark.asyncio(
                loop_scope="module",
                loop_factory=AnotherCustomEventLoop
            )
            async def test_with_a_different_custom_loop_factory():
                ...
            """
        )
    )

    result = pytester.runpytest("--asyncio-mode=strict", "-s", "--setup-show")
    result.assert_outcomes(errors=2)


def test_conflicting_loop_factories_in_tests_and_fixtures_raise_error(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest_asyncio
            import pytest

            class CustomEventLoop(asyncio.SelectorEventLoop):
                pass

            class AnotherCustomEventLoop(asyncio.SelectorEventLoop):
                pass

            @pytest_asyncio.fixture(loop_scope="module", loop_factory=CustomEventLoop)
            async def fixture_with_custom_loop_factory():
                ...

            @pytest.mark.asyncio(
                loop_scope="module",
                loop_factory=AnotherCustomEventLoop
            )
            async def test_trying_to_override_fixtures_loop_factory(
                fixture_with_custom_loop_factory
            ):
                # Fails, because it tries to use a different loop factory on the
                # same runner as the first test
                ...
            """
        )
    )

    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1, errors=1)


def test_conflicting_loop_factories_in_fixtures_raise_error(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest_asyncio
            import pytest

            class CustomEventLoop(asyncio.SelectorEventLoop):
                pass

            class AnotherCustomEventLoop(asyncio.SelectorEventLoop):
                pass

            @pytest_asyncio.fixture(loop_scope="module", loop_factory=CustomEventLoop)
            async def fixture_with_custom_loop_factory():
                ...

            @pytest_asyncio.fixture(
                loop_scope="module",
                loop_factory=AnotherCustomEventLoop
            )
            async def another_fixture_with_custom_loop_factory():
                ...

            @pytest.mark.asyncio(loop_scope="module")
            async def test_requesting_two_fixtures_with_different_loop_facoties(
                fixture_with_custom_loop_factory,
                another_fixture_with_custom_loop_factory,
            ):
                ...
            """
        )
    )

    result = pytester.runpytest("--asyncio-mode=strict", "-s", "--setup-show")
    result.assert_outcomes(errors=1)


def test_conflicting_loop_factories_in_transitive_fixtures_raise_error(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest_asyncio
            import pytest

            class CustomEventLoop(asyncio.SelectorEventLoop):
                pass

            class AnotherCustomEventLoop(asyncio.SelectorEventLoop):
                pass

            @pytest_asyncio.fixture(loop_scope="module", loop_factory=CustomEventLoop)
            async def fixture_with_custom_loop_factory():
                ...

            @pytest_asyncio.fixture(
                loop_scope="module",
                loop_factory=AnotherCustomEventLoop
            )
            async def another_fixture_with_custom_loop_factory(
                fixture_with_custom_loop_factory
            ):
                ...

            @pytest.mark.asyncio(loop_scope="module")
            async def test_requesting_two_fixtures_with_different_loop_facories(
                another_fixture_with_custom_loop_factory,
            ):
                ...
            """
        )
    )

    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(errors=1)
