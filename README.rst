pytest-asyncio: pytest support for asyncio
==========================================

.. image:: https://img.shields.io/pypi/v/pytest-asyncio.svg
    :target: https://pypi.python.org/pypi/pytest-asyncio
.. image:: https://github.com/pytest-dev/pytest-asyncio/workflows/CI/badge.svg
    :target: https://github.com/pytest-dev/pytest-asyncio/actions?workflow=CI
.. image:: https://codecov.io/gh/pytest-dev/pytest-asyncio/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/pytest-dev/pytest-asyncio
.. image:: https://img.shields.io/pypi/pyversions/pytest-asyncio.svg
    :target: https://github.com/pytest-dev/pytest-asyncio
    :alt: Supported Python versions
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

pytest-asyncio is an Apache2 licensed library, written in Python, for testing
asyncio code with pytest.

asyncio code is usually written in the form of coroutines, which makes it
slightly more difficult to test using normal testing tools. pytest-asyncio
provides useful fixtures and markers to make testing easier.

.. code-block:: python

    @pytest.mark.asyncio
    async def test_some_asyncio_code():
        res = await library.do_something()
        assert b"expected result" == res

pytest-asyncio has been strongly influenced by pytest-tornado_.

.. _pytest-tornado: https://github.com/eugeniy/pytest-tornado

Features
--------

- fixtures for creating and injecting versions of the asyncio event loop
- fixtures for injecting unused tcp/udp ports
- pytest markers for treating tests as asyncio coroutines
- easy testing with non-default event loops
- support for `async def` fixtures and async generator fixtures
- support *auto* mode to handle all async fixtures and tests automatically by asyncio;
  provide *strict* mode if a test suite should work with different async frameworks
  simultaneously, e.g. ``asyncio`` and ``trio``.

Installation
------------

To install pytest-asyncio, simply:

.. code-block:: bash

    $ pip install pytest-asyncio

This is enough for pytest to pick up pytest-asyncio.

Modes
-----

Starting from ``pytest-asyncio>=0.17``, three modes are provided: *auto*, *strict* and
*legacy* (default).

The mode can be set by ``asyncio_mode`` configuration option in `configuration file
<https://docs.pytest.org/en/latest/reference/customize.html>`_:

.. code-block:: ini

   # pytest.ini
   [pytest]
   asyncio_mode = auto

The value can be overridden by command-line option for ``pytest`` invocation:

.. code-block:: bash

   $ pytest tests --asyncio-mode=strict

Auto mode
~~~~~~~~~

When the mode is auto, all discovered *async* tests are considered *asyncio-driven* even
if they have no ``@pytest.mark.asyncio`` marker.

All async fixtures are considered *asyncio-driven* as well, even if they are decorated
with a regular ``@pytest.fixture`` decorator instead of dedicated
``@pytest_asyncio.fixture`` counterpart.

*asyncio-driven* means that tests and fixtures are executed by ``pytest-asyncio``
plugin.

This mode requires the simplest tests and fixtures configuration and is
recommended for default usage *unless* the same project and its test suite should
execute tests from different async frameworks, e.g. ``asyncio`` and ``trio``.  In this
case, auto-handling can break tests designed for other framework; please use *strict*
mode instead.

Strict mode
~~~~~~~~~~~

Strict mode enforces ``@pytest.mark.asyncio`` and ``@pytest_asyncio.fixture`` usage.
Without these markers, tests and fixtures are not considered as *asyncio-driven*, other
pytest plugin can handle them.

Please use this mode if multiple async frameworks should be combined in the same test
suite.


Legacy mode
~~~~~~~~~~~

This mode follows rules used by ``pytest-asyncio<0.17``: tests are not auto-marked but
fixtures are.

This mode is used by default for the sake of backward compatibility, deprecation
warnings are emitted with suggestion to either switching to ``auto`` mode or using
``strict`` mode with ``@pytest_asyncio.fixture`` decorators.

In future, the default will be changed.


Fixtures
--------

``event_loop``
~~~~~~~~~~~~~~
Creates and injects a new instance of the default asyncio event loop. By
default, the loop will be closed at the end of the test (i.e. the default
fixture scope is ``function``).

Note that just using the ``event_loop`` fixture won't make your test function
a coroutine. You'll need to interact with the event loop directly, using methods
like ``event_loop.run_until_complete``. See the ``pytest.mark.asyncio`` marker
for treating test functions like coroutines.

Simply using this fixture will not set the generated event loop as the
default asyncio event loop, or change the asyncio event loop policy in any way.
Use ``pytest.mark.asyncio`` for this purpose.

.. code-block:: python

    def test_http_client(event_loop):
        url = "http://httpbin.org/get"
        resp = event_loop.run_until_complete(http_client(url))
        assert b"HTTP/1.1 200 OK" in resp

This fixture can be easily overridden in any of the standard pytest locations
(e.g. directly in the test file, or in ``conftest.py``) to use a non-default
event loop. This will take effect even if you're using the
``pytest.mark.asyncio`` marker and not the ``event_loop`` fixture directly.

.. code-block:: python

    @pytest.fixture
    def event_loop():
        loop = MyCustomLoop()
        yield loop
        loop.close()

If the ``pytest.mark.asyncio`` marker is applied, a pytest hook will
ensure the produced loop is set as the default global loop.
Fixtures depending on the ``event_loop`` fixture can expect the policy to be properly modified when they run.

``unused_tcp_port``
~~~~~~~~~~~~~~~~~~~
Finds and yields a single unused TCP port on the localhost interface. Useful for
binding temporary test servers.

``unused_tcp_port_factory``
~~~~~~~~~~~~~~~~~~~~~~~~~~~
A callable which returns a different unused TCP port each invocation. Useful
when several unused TCP ports are required in a test.

.. code-block:: python

    def a_test(unused_tcp_port_factory):
        port1, port2 = unused_tcp_port_factory(), unused_tcp_port_factory()
        ...

``unused_udp_port`` and ``unused_udp_port_factory``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Work just like their TCP counterparts but return unused UDP ports.


Async fixtures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Asynchronous fixtures are defined just like ordinary pytest fixtures, except they should be decorated with ``@pytest_asyncio.fixture``.

.. code-block:: python3

    import pytest_asyncio


    @pytest_asyncio.fixture
    async def async_gen_fixture():
        await asyncio.sleep(0.1)
        yield "a value"


    @pytest_asyncio.fixture(scope="module")
    async def async_fixture():
        return await asyncio.sleep(0.1)

All scopes are supported, but if you use a non-function scope you will need
to redefine the ``event_loop`` fixture to have the same or broader scope.
Async fixtures need the event loop, and so must have the same or narrower scope
than the ``event_loop`` fixture.

*auto* and *legacy* mode automatically converts async fixtures declared with the
standard ``@pytest.fixture`` decorator to *asyncio-driven* versions.


Markers
-------

``pytest.mark.asyncio``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Mark your test coroutine with this marker and pytest will execute it as an
asyncio task using the event loop provided by the ``event_loop`` fixture. See
the introductory section for an example.

The event loop used can be overridden by overriding the ``event_loop`` fixture
(see above).

In order to make your test code a little more concise, the pytest |pytestmark|_
feature can be used to mark entire modules or classes with this marker.
Only test coroutines will be affected (by default, coroutines prefixed by
``test_``), so, for example, fixtures are safe to define.

.. code-block:: python

    import asyncio

    import pytest

    # All test coroutines will be treated as marked.
    pytestmark = pytest.mark.asyncio


    async def test_example(event_loop):
        """No marker!"""
        await asyncio.sleep(0, loop=event_loop)

In *auto* mode, the ``pytest.mark.asyncio`` marker can be omitted, the marker is added
automatically to *async* test functions.


.. |pytestmark| replace:: ``pytestmark``
.. _pytestmark: http://doc.pytest.org/en/latest/example/markers.html#marking-whole-classes-or-modules

Note about unittest
-------------------

Test classes subclassing the standard `unittest <https://docs.python.org/3/library/unittest.html>`__ library are not supported, users
are recommended to use `unitest.IsolatedAsyncioTestCase <https://docs.python.org/3/library/unittest.html#unittest.IsolatedAsyncioTestCase>`__
or an async framework such as `asynctest <https://asynctest.readthedocs.io/en/latest>`__.

Changelog
---------

0.18.2 (22-03-03)
~~~~~~~~~~~~~~~~~~~
- Fix asyncio auto mode not marking static methods. `#295 <https://github.com/pytest-dev/pytest-asyncio/issues/295>`_
- Fix a compatibility issue with Hypothesis 6.39.0. `#302 <https://github.com/pytest-dev/pytest-asyncio/issues/302>`_


0.18.1 (22-02-10)
~~~~~~~~~~~~~~~~~~~
- Fixes a regression that prevented async fixtures from working in synchronous tests. `#286 <https://github.com/pytest-dev/pytest-asyncio/issues/286>`_

0.18.0 (22-02-07)
~~~~~~~~~~~~~~~~~~~

- Raise a warning if @pytest.mark.asyncio is applied to non-async function. `#275 <https://github.com/pytest-dev/pytest-asyncio/issues/275>`_
- Support parametrized ``event_loop`` fixture. `#278 <https://github.com/pytest-dev/pytest-asyncio/issues/278>`_

0.17.2 (22-01-17)
~~~~~~~~~~~~~~~~~~~

- Require ``typing-extensions`` on Python<3.8 only. `#269 <https://github.com/pytest-dev/pytest-asyncio/issues/269>`_
- Fix a regression in tests collection introduced by 0.17.1, the plugin works fine with non-python tests again. `#267 <https://github.com/pytest-dev/pytest-asyncio/issues/267>`_


0.17.1 (22-01-16)
~~~~~~~~~~~~~~~~~~~
- Fixes a bug that prevents async Hypothesis tests from working without explicit ``asyncio`` marker when ``--asyncio-mode=auto`` is set. `#258 <https://github.com/pytest-dev/pytest-asyncio/issues/258>`_
- Fixed a bug that closes the default event loop if the loop doesn't exist `#257 <https://github.com/pytest-dev/pytest-asyncio/issues/257>`_
- Added type annotations. `#198 <https://github.com/pytest-dev/pytest-asyncio/issues/198>`_
- Show asyncio mode in pytest report headers. `#266 <https://github.com/pytest-dev/pytest-asyncio/issues/266>`_
- Relax ``asyncio_mode`` type definition; it allows to support pytest 6.1+. `#262 <https://github.com/pytest-dev/pytest-asyncio/issues/262>`_

0.17.0 (22-01-13)
~~~~~~~~~~~~~~~~~~~
- `pytest-asyncio` no longer alters existing event loop policies. `#168 <https://github.com/pytest-dev/pytest-asyncio/issues/168>`_, `#188 <https://github.com/pytest-dev/pytest-asyncio/issues/168>`_
- Drop support for Python 3.6
- Fixed an issue when pytest-asyncio was used in combination with `flaky` or inherited asynchronous Hypothesis tests. `#178 <https://github.com/pytest-dev/pytest-asyncio/issues/178>`_ `#231 <https://github.com/pytest-dev/pytest-asyncio/issues/231>`_
- Added `flaky <https://pypi.org/project/flaky/>`_ to test dependencies
- Added ``unused_udp_port`` and ``unused_udp_port_factory`` fixtures (similar to ``unused_tcp_port`` and ``unused_tcp_port_factory`` counterparts. `#99 <https://github.com/pytest-dev/pytest-asyncio/issues/99>`_
- Added the plugin modes: *strict*, *auto*, and *legacy*. See `documentation <https://github.com/pytest-dev/pytest-asyncio#modes>`_ for details. `#125 <https://github.com/pytest-dev/pytest-asyncio/issues/125>`_
- Correctly process ``KeyboardInterrupt`` during async fixture setup phase `#219 <https://github.com/pytest-dev/pytest-asyncio/issues/219>`_

0.16.0 (2021-10-16)
~~~~~~~~~~~~~~~~~~~
- Add support for Python 3.10

0.15.1 (2021-04-22)
~~~~~~~~~~~~~~~~~~~
- Hotfix for errors while closing event loops while replacing them.
  `#209 <https://github.com/pytest-dev/pytest-asyncio/issues/209>`_
  `#210 <https://github.com/pytest-dev/pytest-asyncio/issues/210>`_

0.15.0 (2021-04-19)
~~~~~~~~~~~~~~~~~~~
- Add support for Python 3.9
- Abandon support for Python 3.5. If you still require support for Python 3.5, please use pytest-asyncio v0.14 or earlier.
- Set ``unused_tcp_port_factory`` fixture scope to 'session'.
  `#163 <https://github.com/pytest-dev/pytest-asyncio/pull/163>`_
- Properly close event loops when replacing them.
  `#208 <https://github.com/pytest-dev/pytest-asyncio/issues/208>`_

0.14.0 (2020-06-24)
~~~~~~~~~~~~~~~~~~~
- Fix `#162 <https://github.com/pytest-dev/pytest-asyncio/issues/162>`_, and ``event_loop`` fixture behavior now is coherent on all scopes.
  `#164 <https://github.com/pytest-dev/pytest-asyncio/pull/164>`_

0.12.0 (2020-05-04)
~~~~~~~~~~~~~~~~~~~
- Run the event loop fixture as soon as possible. This helps with fixtures that have an implicit dependency on the event loop.
  `#156 <https://github.com/pytest-dev/pytest-asyncio/pull/156>`_

0.11.0 (2020-04-20)
~~~~~~~~~~~~~~~~~~~
- Test on 3.8, drop 3.3 and 3.4. Stick to 0.10 for these versions.
  `#152 <https://github.com/pytest-dev/pytest-asyncio/pull/152>`_
- Use the new Pytest 5.4.0 Function API. We therefore depend on pytest >= 5.4.0.
  `#142 <https://github.com/pytest-dev/pytest-asyncio/pull/142>`_
- Better ``pytest.skip`` support.
  `#126 <https://github.com/pytest-dev/pytest-asyncio/pull/126>`_

0.10.0 (2019-01-08)
~~~~~~~~~~~~~~~~~~~~
- ``pytest-asyncio`` integrates with `Hypothesis <https://hypothesis.readthedocs.io>`_
  to support ``@given`` on async test functions using ``asyncio``.
  `#102 <https://github.com/pytest-dev/pytest-asyncio/pull/102>`_
- Pytest 4.1 support.
  `#105 <https://github.com/pytest-dev/pytest-asyncio/pull/105>`_

0.9.0 (2018-07-28)
~~~~~~~~~~~~~~~~~~
- Python 3.7 support.
- Remove ``event_loop_process_pool`` fixture and
  ``pytest.mark.asyncio_process_pool`` marker (see
  https://bugs.python.org/issue34075 for deprecation and removal details)

0.8.0 (2017-09-23)
~~~~~~~~~~~~~~~~~~
- Improve integration with other packages (like aiohttp) with more careful event loop handling.
  `#64 <https://github.com/pytest-dev/pytest-asyncio/pull/64>`_

0.7.0 (2017-09-08)
~~~~~~~~~~~~~~~~~~
- Python versions pre-3.6 can use the async_generator library for async fixtures.
  `#62 <https://github.com/pytest-dev/pytest-asyncio/pull/62>`


0.6.0 (2017-05-28)
~~~~~~~~~~~~~~~~~~
- Support for Python versions pre-3.5 has been dropped.
- ``pytestmark`` now works on both module and class level.
- The ``forbid_global_loop`` parameter has been removed.
- Support for async and async gen fixtures has been added.
  `#45 <https://github.com/pytest-dev/pytest-asyncio/pull/45>`_
- The deprecation warning regarding ``asyncio.async()`` has been fixed.
  `#51 <https://github.com/pytest-dev/pytest-asyncio/pull/51>`_

0.5.0 (2016-09-07)
~~~~~~~~~~~~~~~~~~
- Introduced a changelog.
  `#31 <https://github.com/pytest-dev/pytest-asyncio/issues/31>`_
- The ``event_loop`` fixture is again responsible for closing itself.
  This makes the fixture slightly harder to correctly override, but enables
  other fixtures to depend on it correctly.
  `#30 <https://github.com/pytest-dev/pytest-asyncio/issues/30>`_
- Deal with the event loop policy by wrapping a special pytest hook,
  ``pytest_fixture_setup``. This allows setting the policy before fixtures
  dependent on the ``event_loop`` fixture run, thus allowing them to take
  advantage of the ``forbid_global_loop`` parameter. As a consequence of this,
  we now depend on pytest 3.0.
  `#29 <https://github.com/pytest-dev/pytest-asyncio/issues/29>`_


0.4.1 (2016-06-01)
~~~~~~~~~~~~~~~~~~
- Fix a bug preventing the propagation of exceptions from the plugin.
  `#25 <https://github.com/pytest-dev/pytest-asyncio/issues/25>`_

0.4.0 (2016-05-30)
~~~~~~~~~~~~~~~~~~
- Make ``event_loop`` fixtures simpler to override by closing them in the
  plugin, instead of directly in the fixture.
  `#21 <https://github.com/pytest-dev/pytest-asyncio/pull/21>`_
- Introduce the ``forbid_global_loop`` parameter.
  `#21 <https://github.com/pytest-dev/pytest-asyncio/pull/21>`_

0.3.0 (2015-12-19)
~~~~~~~~~~~~~~~~~~
- Support for Python 3.5 ``async``/``await`` syntax.
  `#17 <https://github.com/pytest-dev/pytest-asyncio/pull/17>`_

0.2.0 (2015-08-01)
~~~~~~~~~~~~~~~~~~
- ``unused_tcp_port_factory`` fixture.
  `#10 <https://github.com/pytest-dev/pytest-asyncio/issues/10>`_


0.1.1 (2015-04-23)
~~~~~~~~~~~~~~~~~~
Initial release.


Contributing
------------
Contributions are very welcome. Tests can be run with ``tox``, please ensure
the coverage at least stays the same before you submit a pull request.
