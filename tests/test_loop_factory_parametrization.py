from __future__ import annotations

from textwrap import dedent

import pytest
from pytest import Pytester


@pytest.mark.skipif(
    not hasattr(pytest, "HIDDEN_PARAM"),
    reason="pytest.HIDDEN_PARAM requires pytest 9.0+",
)
def test_single_factory_does_not_add_suffix_to_test_name(
    pytester: Pytester,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        def pytest_asyncio_loop_factories(config, item):
            return {"asyncio": asyncio.new_event_loop}
        """))
    pytester.makepyfile(dedent("""\
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_example():
            assert True
        """))
    result = pytester.runpytest("--asyncio-mode=strict", "--collect-only", "-q")
    result.stdout.fnmatch_lines(
        ["test_single_factory_does_not_add_suffix_to_test_name.py::test_example"]
    )


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
            assert True

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


def test_nested_conftest_hook_respects_conftest_locality(
    pytester: Pytester,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class RootCustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return {"root": RootCustomEventLoop}
        """))
    subdir = pytester.mkdir("subdir")
    subdir.joinpath("conftest.py").write_text(
        dedent("""\
        import asyncio

        class SubCustomEventLoop(asyncio.SelectorEventLoop):
            pass

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
            async def test_root_uses_root_loop():
                assert (
                    type(asyncio.get_running_loop()).__name__ == "RootCustomEventLoop"
                )
            """),
    )
    subdir.joinpath("test_sub.py").write_text(
        dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_sub_uses_sub_loop():
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


def test_no_event_loop_leak_with_custom_factory(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio
        import pytest_asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return {"custom": CustomEventLoop}

        @pytest_asyncio.fixture(autouse=True, scope="session", loop_scope="session")
        async def session_fixture():
            yield

        @pytest_asyncio.fixture(autouse=True)
        def sync_fixture():
            asyncio.get_event_loop()
        """))
    pytester.makepyfile(dedent("""\
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_passes():
            assert True
        """))
    result = pytester.runpytest_subprocess(
        "--asyncio-mode=auto", "-W", "error::ResourceWarning"
    )
    result.assert_outcomes(passed=1)
    result.stderr.no_fnmatch_line("*unclosed event loop*")


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


def test_sync_fixture_sees_same_loop_as_async_test_under_custom_factory(
    pytester: Pytester,
) -> None:
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

        @pytest_asyncio.fixture(autouse=True)
        def enable_debug_on_event_loop():
            asyncio.get_event_loop().set_debug(True)

        @pytest.mark.asyncio
        async def test_debug_mode_visible():
            assert asyncio.get_running_loop().get_debug()
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    ("fixture_scope", "wider_scope"),
    [
        ("function", "module"),
        ("function", "package"),
        ("function", "session"),
        ("module", "session"),
        ("package", "session"),
    ],
)
def test_sync_fixture_sees_its_own_loop_when_wider_scoped_loop_active(
    pytester: Pytester,
    fixture_scope: str,
    wider_scope: str,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent(f"""\
        import asyncio
        import pytest_asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return {{"custom": CustomEventLoop}}

        @pytest_asyncio.fixture(
            autouse=True,
            scope="{wider_scope}",
            loop_scope="{wider_scope}",
        )
        async def wider_scoped_fixture():
            yield

        @pytest_asyncio.fixture(
            autouse=True,
            scope="{fixture_scope}",
            loop_scope="{fixture_scope}",
        )
        def sync_fixture_captures_loop():
            return id(asyncio.get_event_loop())
        """))
    pytester.makepyfile(dedent(f"""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio(loop_scope="{fixture_scope}")
        async def test_sync_fixture_and_test_see_same_loop(sync_fixture_captures_loop):
            assert sync_fixture_captures_loop == id(asyncio.get_running_loop())
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    ("fixture_scope", "wider_scope"),
    [
        ("function", "module"),
        ("function", "session"),
        ("module", "session"),
    ],
)
def test_sync_generator_fixture_teardown_sees_own_loop(
    pytester: Pytester,
    fixture_scope: str,
    wider_scope: str,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent(f"""\
        import asyncio
        import pytest_asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return {{"custom": CustomEventLoop}}

        @pytest_asyncio.fixture(
            autouse=True,
            scope="{wider_scope}",
            loop_scope="{wider_scope}",
        )
        async def wider_scoped_fixture():
            yield

        @pytest_asyncio.fixture(
            autouse=True,
            scope="{fixture_scope}",
            loop_scope="{fixture_scope}",
        )
        def sync_generator_fixture():
            loop_at_setup = id(asyncio.get_event_loop())
            yield loop_at_setup
            loop_at_teardown = id(asyncio.get_event_loop())
            assert loop_at_setup == loop_at_teardown
        """))
    pytester.makepyfile(dedent(f"""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio(loop_scope="{fixture_scope}")
        async def test_generator_fixture_sees_correct_loop(sync_generator_fixture):
            assert sync_generator_fixture == id(asyncio.get_running_loop())
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize("loop_scope", ("module", "package", "session"))
def test_async_generator_fixture_teardown_runs_under_custom_factory(
    pytester: Pytester,
    loop_scope: str,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent(f"""\
        import asyncio
        import pytest_asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return {{"custom": CustomEventLoop}}

        @pytest_asyncio.fixture(
            autouse=True, scope="{loop_scope}", loop_scope="{loop_scope}"
        )
        async def fixture_with_teardown():
            yield
            print("TEARDOWN_EXECUTED")
        """))
    pytester.makepyfile(dedent(f"""\
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio(loop_scope="{loop_scope}")
        async def test_passes():
            assert True
        """))
    result = pytester.runpytest("--asyncio-mode=strict", "-s")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*TEARDOWN_EXECUTED*"])


@pytest.mark.parametrize("loop_scope", ("module", "package", "session"))
def test_async_fixture_recreated_per_loop_factory_variant(
    pytester: Pytester,
    loop_scope: str,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent(f"""\
        import asyncio
        import pytest_asyncio

        class CustomLoopA(asyncio.SelectorEventLoop):
            pass

        class CustomLoopB(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return {{"loop_a": CustomLoopA, "loop_b": CustomLoopB}}

        @pytest_asyncio.fixture(scope="{loop_scope}", loop_scope="{loop_scope}")
        async def fixture_loop_type():
            return type(asyncio.get_running_loop()).__name__
        """))
    pytester.makepyfile(dedent(f"""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio(loop_scope="{loop_scope}")
        async def test_fixture_matches_running_loop(fixture_loop_type):
            running_loop_type = type(asyncio.get_running_loop()).__name__
            assert fixture_loop_type == running_loop_type
        """))
    result = pytester.runpytest("--asyncio-mode=strict", "-v")
    result.assert_outcomes(passed=2)
