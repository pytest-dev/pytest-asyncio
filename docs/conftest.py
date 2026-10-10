import sys

collect_ignore = []
if sys.version_info < (3, 11):
    # asyncio.timeout requires Python 3.11.
    collect_ignore.append("concepts_fixture_deadline_example.py")
