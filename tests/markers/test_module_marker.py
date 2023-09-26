from textwrap import dedent

from pytest import Pytester


def test_asyncio_mark_works_on_module_level(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio

            import pytest

            pytestmark = pytest.mark.asyncio


            class TestPyTestMark:
                async def test_is_asyncio(self, event_loop, sample_fixture):
                    assert asyncio.get_event_loop()

                    counter = 1

                    async def inc():
                        nonlocal counter
                        counter += 1
                        await asyncio.sleep(0)

                    await asyncio.ensure_future(inc())
                    assert counter == 2


            async def test_is_asyncio(event_loop, sample_fixture):
                assert asyncio.get_event_loop()
                counter = 1

                async def inc():
                    nonlocal counter
                    counter += 1
                    await asyncio.sleep(0)

                await asyncio.ensure_future(inc())
                assert counter == 2


            @pytest.fixture
            def sample_fixture():
                return None
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)
