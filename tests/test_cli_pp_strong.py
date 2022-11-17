#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for `of.cli_pp_strong ` CLI."""

from click.testing import CliRunner

from of.cli_pp_strong import main


def test_main():
    runner = CliRunner()
    result = runner.invoke(main, ['-vv'])
    print(result.output)
    assert 'running' in result.output

# ==============================================================================
# The code below is for debugging a particular test in eclipse/pydev.
# (normally all tests are run with pytest)
# ==============================================================================
if __name__ == "__main__":
    the_test_you_want_to_debug = test_main

    print(f"__main__ running {the_test_you_want_to_debug}")
    the_test_you_want_to_debug()
    print('-*# finished #*-')
# eof
