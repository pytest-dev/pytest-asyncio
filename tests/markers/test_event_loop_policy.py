from textwrap import dedent

from pytest import Pytester


def test_parametrized_loop_policy_does_not_parametrize_sync_tests(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            import asyncio

            import pytest

            class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
                pass

            @pytest.fixture(
                params=[
                    asyncio.DefaultEventLoopPolicy(),
                    CustomEventLoopPolicy(),
                ],
            )
            def event_loop_policy(request):
                return request.param

            @pytest.mark.asyncio
            async def test_async():
                assert isinstance(
                    asyncio.get_event_loop_policy(),
                    (asyncio.DefaultEventLoopPolicy, CustomEventLoopPolicy),
                )

            def test_sync():
                assert True
            """))

    result = pytester.runpytest("--asyncio-mode=strict")

    result.assert_outcomes(passed=3)
