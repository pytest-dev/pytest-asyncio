from __future__ import annotations

from textwrap import dedent

import pytest
from pytest import PytestDeprecationWarning, Pytester

import pytest_asyncio.plugin


def test_unused_tcp_port_selects_unused_port(pytester: Pytester):
    pytester.makepyfile(dedent("""\
            import asyncio

            import pytest

            @pytest.mark.asyncio
            async def test_unused_port_fixture(unused_tcp_port):
                async def closer(_, writer):
                    writer.close()

                server1 = await asyncio.start_server(
                    closer, host="localhost", port=unused_tcp_port
                )

                with pytest.raises(IOError):
                    await asyncio.start_server(
                        closer, host="localhost", port=unused_tcp_port
                    )

                server1.close()
                await server1.wait_closed()
            """))


def test_unused_udp_port_selects_unused_port(pytester: Pytester):
    pytester.makepyfile(dedent("""\
            @pytest.mark.asyncio
            async def test_unused_udp_port_fixture(unused_udp_port):
                class Closer:
                    def connection_made(self, transport):
                        pass

                    def connection_lost(self, *arg, **kwd):
                        pass

                event_loop = asyncio.get_running_loop()
                transport1, _ = await event_loop.create_datagram_endpoint(
                    Closer,
                    local_addr=("127.0.0.1", unused_udp_port),
                    reuse_port=False,
                )

                with pytest.raises(IOError):
                    await event_loop.create_datagram_endpoint(
                        Closer,
                        local_addr=("127.0.0.1", unused_udp_port),
                        reuse_port=False,
                    )

                transport1.abort()
            """))


def test_unused_tcp_port_factory_selects_unused_port(pytester: Pytester):
    pytester.makepyfile(dedent("""\
            @pytest.mark.asyncio
            async def test_unused_port_factory_fixture(unused_tcp_port_factory):
                async def closer(_, writer):
                    writer.close()

                port1, port2, port3 = (
                    unused_tcp_port_factory(),
                    unused_tcp_port_factory(),
                    unused_tcp_port_factory(),
                )

                server1 = await asyncio.start_server(
                    closer, host="localhost", port=port1
                )
                server2 = await asyncio.start_server(
                    closer, host="localhost", port=port2
                )
                server3 = await asyncio.start_server(
                    closer, host="localhost", port=port3
                )

                for port in port1, port2, port3:
                    with pytest.raises(IOError):
                        await asyncio.start_server(closer, host="localhost", port=port)

                server1.close()
                await server1.wait_closed()
                server2.close()
                await server2.wait_closed()
                server3.close()
                await server3.wait_closed()
            """))


def test_unused_udp_port_factory_selects_unused_port(pytester: Pytester):
    pytester.makepyfile(dedent("""\
            @pytest.mark.asyncio
            async def test_unused_udp_port_factory_fixture(unused_udp_port_factory):
                class Closer:
                    def connection_made(self, transport):
                        pass

                    def connection_lost(self, *arg, **kwd):
                        pass

                port1, port2, port3 = (
                    unused_udp_port_factory(),
                    unused_udp_port_factory(),
                    unused_udp_port_factory(),
                )

                event_loop = asyncio.get_running_loop()
                transport1, _ = await event_loop.create_datagram_endpoint(
                    Closer,
                    local_addr=("127.0.0.1", port1),
                    reuse_port=False,
                )
                transport2, _ = await event_loop.create_datagram_endpoint(
                    Closer,
                    local_addr=("127.0.0.1", port2),
                    reuse_port=False,
                )
                transport3, _ = await event_loop.create_datagram_endpoint(
                    Closer,
                    local_addr=("127.0.0.1", port3),
                    reuse_port=False,
                )

                for port in port1, port2, port3:
                    with pytest.raises(IOError):
                        await event_loop.create_datagram_endpoint(
                            Closer,
                            local_addr=("127.0.0.1", port),
                            reuse_port=False,
                        )

                transport1.abort()
                transport2.abort()
                transport3.abort()
            """))


def test_unused_port_factory_duplicate(request, monkeypatch):
    """Test correct avoidance of duplicate ports."""
    counter = 0

    def mock_unused_tcp_port(_ignored):
        """Force some duplicate ports."""
        nonlocal counter
        counter += 1
        if counter < 5:
            return 10000
        else:
            return 10000 + counter

    monkeypatch.setattr(pytest_asyncio.plugin, "_unused_port", mock_unused_tcp_port)

    with pytest.warns(
        PytestDeprecationWarning, match="unused_tcp_port_factory fixture is deprecated"
    ):
        unused_tcp_port_factory = request.getfixturevalue("unused_tcp_port_factory")

    assert unused_tcp_port_factory() == 10000
    assert unused_tcp_port_factory() > 10000


def test_unused_udp_port_factory_duplicate(request, monkeypatch):
    """Test correct avoidance of duplicate UDP ports."""
    counter = 0

    def mock_unused_udp_port(_ignored):
        """Force some duplicate ports."""
        nonlocal counter
        counter += 1
        if counter < 5:
            return 10000
        else:
            return 10000 + counter

    monkeypatch.setattr(pytest_asyncio.plugin, "_unused_port", mock_unused_udp_port)

    with pytest.warns(
        PytestDeprecationWarning, match="unused_udp_port_factory fixture is deprecated"
    ):
        unused_udp_port_factory = request.getfixturevalue("unused_udp_port_factory")

    assert unused_udp_port_factory() == 10000
    assert unused_udp_port_factory() > 10000


@pytest.mark.parametrize(
    "fixture_name",
    [
        "unused_tcp_port",
        "unused_udp_port",
    ],
)
def test_unused_port_fixtures_are_deprecated(request, fixture_name):
    """Requesting an unused port fixture emits a deprecation warning."""
    with pytest.warns(
        PytestDeprecationWarning, match=f"{fixture_name} fixture is deprecated"
    ):
        fixture = request.getfixturevalue(fixture_name)
    # The fixture still works while it is deprecated.
    assert isinstance(fixture, int)


def test_unused_port_fixtures_warn_on_use(pytester: Pytester):
    """Requesting any unused port fixture emits a deprecation warning."""
    pytester.makepyfile(dedent("""\
        import pytest


        @pytest.mark.parametrize(
            "fixture_name",
            [
                "unused_tcp_port",
                "unused_udp_port",
                "unused_tcp_port_factory",
                "unused_udp_port_factory",
            ],
        )
        def test_fixture_emits_deprecation_warning(request, fixture_name):
            with pytest.warns(
                pytest.PytestDeprecationWarning,
                match=f"{fixture_name} fixture is deprecated",
            ):
                fixture = request.getfixturevalue(fixture_name)
            # The fixture still works while it is deprecated.
            if callable(fixture):
                assert isinstance(fixture(), int)
            else:
                assert isinstance(fixture, int)
        """))
    result = pytester.runpytest()
    result.assert_outcomes(passed=4)
