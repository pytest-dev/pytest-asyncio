======================================
How to test with different event loops
======================================

Parametrizing the *event_loop_policy* fixture parametrizes all async tests. The following example causes all async tests to run multiple times, once for each event loop in the fixture parameters:

.. include:: multiple_loops_example.py
    :code: python

You may choose to limit the scope of the fixture to *package,* *module,* or *class,* if you only want a subset of your tests to run with different event loops.
