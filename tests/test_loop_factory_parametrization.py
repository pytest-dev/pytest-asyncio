from __future__ import annotations

from textwrap import dedent

import pytest
from pytest import Pytester


def test_named_hook_factories_apply_to_async_tests(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return {"custom": CustomEventLoop}
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_uses_custom_loop():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoop"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_named_hook_factories_parametrize_async_tests(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoopA(asyncio.SelectorEventLoop):
            pass

        class CustomEventLoopB(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return {
                "factory_a": CustomEventLoopA,
                "factory_b": CustomEventLoopB,
            }
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_runs_once_per_factory():
            loop_name = type(asyncio.get_running_loop()).__name__
            assert loop_name in ("CustomEventLoopA", "CustomEventLoopB")
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_named_hook_factories_use_mapping_keys_as_test_ids(
    pytester: Pytester,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        def pytest_asyncio_loop_factories(config, item):
            return {
                "factory_a": asyncio.new_event_loop,
                "factory_b": asyncio.new_event_loop,
            }
        """))
    pytester.makepyfile(dedent("""\
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_runs_once_per_factory():
            assert True
        """))
    result = pytester.runpytest("--asyncio-mode=strict", "--collect-only", "-q")
    result.stdout.fnmatch_lines(
        [
            "*test_runs_once_per_factory[[]factory_a[]]",
            "*test_runs_once_per_factory[[]factory_b[]]",
        ]
    )


def test_named_hook_factories_apply_to_async_fixtures(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return {"custom": CustomEventLoop}
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest
        import pytest_asyncio

        pytest_plugins = "pytest_asyncio"

        @pytest_asyncio.fixture
        async def loop_fixture():
            return asyncio.get_running_loop()

        @pytest.mark.asyncio
        async def test_fixture_uses_custom_loop(loop_fixture):
            assert type(loop_fixture).__name__ == "CustomEventLoop"
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoop"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_sync_tests_are_not_parametrized_by_hook_factories(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoopA(asyncio.SelectorEventLoop):
            pass

        class CustomEventLoopB(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return {
                "factory_a": CustomEventLoopA,
                "factory_b": CustomEventLoopB,
            }
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        def test_sync(request):
            assert "_asyncio_loop_factory" not in request.fixturenames

        @pytest.mark.asyncio
        async def test_async(request):
            assert "_asyncio_loop_factory" in request.fixturenames
            loop_name = type(asyncio.get_running_loop()).__name__
            assert loop_name in ("CustomEventLoopA", "CustomEventLoopB")
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=3)


@pytest.mark.parametrize(
    "hook_body",
    (
        "return None",
        "return {}",
        "return [CustomEventLoop]",
        "return {'': CustomEventLoop}",
        "return {'default': 1}",
    ),
)
def test_hook_requires_non_empty_mapping_of_named_callables(
    pytester: Pytester,
    hook_body: str,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent(f"""\
        import asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            {hook_body}
        """))
    pytester.makepyfile(dedent("""\
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_async():
            assert True
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        [
            "*pytest_asyncio_loop_factories must return a non-empty mapping of "
            "factory*"
        ]
    )


def test_hook_factories_use_first_non_none_result(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        plugin_none=dedent("""\
            import pytest

            @pytest.hookimpl(tryfirst=True)
            def pytest_asyncio_loop_factories(config, item):
                return None
            """),
        plugin_loop=dedent("""\
            import asyncio
            import pytest

            class SecondaryCustomEventLoop(asyncio.SelectorEventLoop):
                pass

            @pytest.hookimpl(trylast=True)
            def pytest_asyncio_loop_factories(config, item):
                return {"secondary": SecondaryCustomEventLoop}
            """),
        test_sample=dedent("""\
            import asyncio
            import pytest

            pytest_plugins = ("pytest_asyncio", "plugin_none", "plugin_loop")

            @pytest.mark.asyncio
            async def test_uses_secondary_loop():
                assert (
                    type(asyncio.get_running_loop()).__name__
                    == "SecondaryCustomEventLoop"
                )
            """),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_hook_factories_short_circuit_after_first_non_none_result(
    pytester: Pytester,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        plugin_first=dedent("""\
            import asyncio
            import pytest

            class PrimaryCustomEventLoop(asyncio.SelectorEventLoop):
                pass

            @pytest.hookimpl(tryfirst=True)
            def pytest_asyncio_loop_factories(config, item):
                return {"primary": PrimaryCustomEventLoop}
            """),
        plugin_second=dedent("""\
            import pytest

            @pytest.hookimpl(trylast=True)
            def pytest_asyncio_loop_factories(config, item):
                raise RuntimeError("should not be called")
            """),
        test_sample=dedent("""\
            import asyncio
            import pytest

            pytest_plugins = ("pytest_asyncio", "plugin_first", "plugin_second")

            @pytest.mark.asyncio
            async def test_uses_primary_loop():
                assert (
                    type(asyncio.get_running_loop()).__name__
                    == "PrimaryCustomEventLoop"
                )
            """),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_hook_factories_error_when_all_implementations_return_none(
    pytester: Pytester,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        plugin_none_a=dedent("""\
            import pytest

            @pytest.hookimpl(tryfirst=True)
            def pytest_asyncio_loop_factories(config, item):
                return None
            """),
        plugin_none_b=dedent("""\
            import pytest

            @pytest.hookimpl(trylast=True)
            def pytest_asyncio_loop_factories(config, item):
                return None
            """),
        test_sample=dedent("""\
            import pytest

            pytest_plugins = ("pytest_asyncio", "plugin_none_a", "plugin_none_b")

            @pytest.mark.asyncio
            async def test_anything():
                assert True
            """),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        [
            "*pytest_asyncio_loop_factories must return a non-empty mapping of "
            "factory*"
        ]
    )


def test_nested_conftest_hook_implementations_respect_hook_order(
    pytester: Pytester,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio
        import pytest

        class RootCustomEventLoop(asyncio.SelectorEventLoop):
            pass

        @pytest.hookimpl(trylast=True)
        def pytest_asyncio_loop_factories(config, item):
            return {"root": RootCustomEventLoop}
        """))
    subdir = pytester.mkdir("subtests")
    subdir.joinpath("conftest.py").write_text(
        dedent("""\
        import asyncio
        import pytest

        class SubCustomEventLoop(asyncio.SelectorEventLoop):
            pass

        @pytest.hookimpl(tryfirst=True)
        def pytest_asyncio_loop_factories(config, item):
            return {"sub": SubCustomEventLoop}
        """),
    )
    pytester.makepyfile(
        test_root=dedent("""\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_uses_sub_loop():
                assert type(asyncio.get_running_loop()).__name__ == "SubCustomEventLoop"
            """),
    )
    subdir.joinpath("test_sub.py").write_text(
        dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_uses_sub_loop():
            assert type(asyncio.get_running_loop()).__name__ == "SubCustomEventLoop"
        """),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_marker_loop_factories_select_subset(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class MainCustomEventLoop(asyncio.SelectorEventLoop):
            pass

        class AlternativeCustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return {
                "main": MainCustomEventLoop,
                "alternative": AlternativeCustomEventLoop,
            }
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio(loop_factories=["alternative"])
        async def test_runs_only_with_uvloop():
            assert (
                type(asyncio.get_running_loop()).__name__
                == "AlternativeCustomEventLoop"
            )
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_asyncio_marker_loop_factories_unknown_name_errors(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        def pytest_asyncio_loop_factories(config, item):
            return {"root": asyncio.new_event_loop}
        """))
    pytester.makepyfile(dedent("""\
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio(loop_factories=["missing"])
        async def test_errors():
            assert True
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        [
            "*Unknown factory name(s)*Available names:*",
        ]
    )


def test_asyncio_marker_loop_factories_without_hook_errors(
    pytester: Pytester,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio(loop_factories=["missing"])
        async def test_errors():
            assert True
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        [
            "*mark.asyncio 'loop_factories' requires at least one "
            "pytest_asyncio_loop_factories hook implementation.*",
        ]
    )


@pytest.mark.parametrize("default_test_loop_scope", ("function", "module"))
def test_hook_factories_can_vary_per_test_with_default_loop_scope(
    pytester: Pytester,
    default_test_loop_scope: str,
) -> None:
    pytester.makeini(
        "[pytest]\nasyncio_default_fixture_loop_scope = function\n"
        f"asyncio_default_test_loop_scope = {default_test_loop_scope}"
    )
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoopA(asyncio.SelectorEventLoop):
            pass

        class CustomEventLoopB(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            if item.name.endswith("a"):
                return {"factory_a": CustomEventLoopA}
            else:
                return {"factory_b": CustomEventLoopB}
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_a():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoopA"

        @pytest.mark.asyncio
        async def test_b():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoopB"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_hook_factories_can_vary_per_test_with_session_scope_across_modules(
    pytester: Pytester,
) -> None:
    pytester.makeini(
        "[pytest]\nasyncio_default_fixture_loop_scope = function\n"
        "asyncio_default_test_loop_scope = session"
    )
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoopA(asyncio.SelectorEventLoop):
            pass

        class CustomEventLoopB(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            if "test_a.py::" in item.nodeid:
                return {"factory_a": CustomEventLoopA}
            else:
                return {"factory_b": CustomEventLoopB}
        """))
    pytester.makepyfile(
        test_a=dedent("""\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_a():
                assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoopA"
            """),
        test_b=dedent("""\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_b():
                assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoopB"
            """),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_hook_factories_work_in_auto_mode(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return {"custom": CustomEventLoop}
        """))
    pytester.makepyfile(dedent("""\
        import asyncio

        pytest_plugins = "pytest_asyncio"

        async def test_uses_custom_loop():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoop"
        """))
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)


def test_function_loop_scope_allows_per_test_factories_with_session_default(
    pytester: Pytester,
) -> None:
    pytester.makeini(
        "[pytest]\nasyncio_default_fixture_loop_scope = function\n"
        "asyncio_default_test_loop_scope = session"
    )
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoopA(asyncio.SelectorEventLoop):
            pass

        class CustomEventLoopB(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            if item.name.endswith("a"):
                return {"factory_a": CustomEventLoopA}
            else:
                return {"factory_b": CustomEventLoopB}
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio(loop_scope="function")
        async def test_a():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoopA"

        @pytest.mark.asyncio(loop_scope="function")
        async def test_b():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoopB"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)
