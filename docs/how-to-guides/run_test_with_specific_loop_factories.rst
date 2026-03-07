=========================================================
How to run a test with specific event loop factories only
=========================================================

To run a test with only a subset of configured factories, use the ``loop_factories`` argument of ``pytest.mark.asyncio``:

.. code-block:: python

   import pytest


   @pytest.mark.asyncio(loop_factories=["custom"])
   async def test_only_with_custom_event_loop():
       pass
