import sys

collect_ignore = []
if sys.version_info[:2] < (3, 5):
    collect_ignore.append("test_simple_35.py")
