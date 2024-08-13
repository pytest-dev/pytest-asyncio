==========================
Welcome to pytest-asyncio!
==========================

.. toctree::
  :maxdepth: 1
  :hidden:

  concepts
  how-to-guides/index
  reference/index
  support

pytest-asyncio is a `pytest <https://docs.pytest.org/en/latest/contents.html>`_ plugin. It facilitates testing of code that uses the `asyncio <https://docs.python.org/3/library/asyncio.html>`_ library.

Specifically, pytest-asyncio provides support for coroutines as test functions. This allows users to *await* code inside their tests. For example, the following code is executed as a test item by pytest:

.. code-block:: python

    @pytest.mark.asyncio
    async def test_some_asyncio_code():
        res = await library.do_something()
        assert b"expected result" == res


Note that test classes subclassing the standard `unittest <https://docs.python.org/3/library/unittest.html>`__ library are not supported. Users
are advised to use `unittest.IsolatedAsyncioTestCase <https://docs.python.org/3/library/unittest.html#unittest.IsolatedAsyncioTestCase>`__
or an async framework such as `asynctest <https://asynctest.readthedocs.io/en/latest>`__.


pytest-asyncio is available under the `Apache License 2.0 <https://github.com/pytest-dev/pytest-asyncio/blob/main/LICENSE>`_.
