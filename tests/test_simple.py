"""Quick'n'dirty unit tests for provided fixtures and markers."""
import asyncio
import os
import urllib
import pytest


@asyncio.coroutine
def simple_http_client(url):
    """Just a simple http client, for testing."""
    u = urllib.parse.urlparse(url)
    port = u.port if u.port else 80
    r, w = yield from asyncio.open_connection(host=u.netloc, port=port)
    w.write(b'GET ' + u.path.encode() + b' HTTP/1.0\r\n')
    w.write(b'Host: ' + u.netloc.encode() + b'\r\n')
    w.write(b'\r\n')
    yield from w.drain()

    resp = yield from r.read()

    w.close()
    return resp


def test_event_loop_fixture(event_loop):
    """Test the injection of the event_loop fixture."""
    assert event_loop
    url = 'http://httpbin.org/get'
    resp = event_loop.run_until_complete(simple_http_client(url))
    assert b'HTTP/1.1 200 OK' in resp


def test_event_loop_processpool_fixture(event_loop_process_pool):
    """Test the injection of the event_loop with a process pool fixture."""
    assert event_loop_process_pool
    url = 'http://httpbin.org/get'
    resp = event_loop_process_pool.run_until_complete(simple_http_client(url))
    assert b'HTTP/1.1 200 OK' in resp

    this_pid = os.getpid()
    future = event_loop_process_pool.run_in_executor(None, os.getpid)
    pool_pid = event_loop_process_pool.run_until_complete(future)
    assert this_pid != pool_pid


@pytest.mark.asyncio
def test_asyncio_marker():
    """Test the asyncio pytest marker."""
    url = 'http://httpbin.org/get'
    resp = yield from simple_http_client(url)
    assert b'HTTP/1.1 200 OK' in resp


@pytest.mark.asyncio
def test_asyncio_marker_with_default_param(a_param=None):
    """Test the asyncio pytest marker."""
    url = 'http://httpbin.org/get'
    resp = yield from simple_http_client(url)
    assert b'HTTP/1.1 200 OK' in resp


@pytest.mark.asyncio_process_pool
def test_asyncio_process_pool_marker(event_loop):
    """Test the asyncio pytest marker."""
    url = 'http://httpbin.org/get'
    resp = yield from simple_http_client(url)
    assert b'HTTP/1.1 200 OK' in resp

    this_pid = os.getpid()
    pool_pid = yield from event_loop.run_in_executor(None, os.getpid)
    assert this_pid != pool_pid


@pytest.mark.asyncio
def test_unused_port_fixture(unused_tcp_port):
    """Test the unused TCP port fixture."""

    @asyncio.coroutine
    def closer(_, writer):
        writer.close()

    server1 = yield from asyncio.start_server(closer, host='localhost',
                                              port=unused_tcp_port)

    with pytest.raises(IOError):
        yield from asyncio.start_server(closer, host='localhost',
                                        port=unused_tcp_port)

    server1.close()
    yield from server1.wait_closed()