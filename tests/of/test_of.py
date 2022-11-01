# -*- coding: utf-8 -*-

"""Tests for of package."""

import sys
sys.path.insert(0,'.')

import of


def test_walltime():
    """."""
    for hours in range(0,73):
        w = of.walltime(hours)
        assert w == f"{hours}:00:00"

    hours = 1.5
    assert of.walltime(hours) == f"1:30:00"

# ==============================================================================
# The code below is for debugging a particular test in eclipse/pydev.
# (otherwise all tests are normally run with pytest)
# Make sure that you run this code with the project directory as CWD, and
# that the source directory is on the path
# ==============================================================================
if __name__ == "__main__":
    the_test_you_want_to_debug = test_walltime

    print("__main__ running", the_test_you_want_to_debug)
    the_test_you_want_to_debug()
    print('-*# finished #*-')

# eof