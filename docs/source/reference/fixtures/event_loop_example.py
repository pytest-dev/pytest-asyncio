import asyncio


def test_event_loop_fixture(event_loop):
    event_loop.run_until_complete(asyncio.sleep(0))
