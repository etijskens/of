# -*- coding: utf-8 -*-
"""Command line interface pp-strong (no sub-commands)."""

import sys

import click


@click.command()
@click.option('-c','--case'
             , help='name of the OpenFOAM case directory.'
             )
@click.option('-l','--location'
             , help='Location where the results were computed.'
             , default='.'
             )
@click.option('-v', '--verbosity', count=True
             , help="The verbosity of the program."
             , default=1
             )
def main(case, location, verbosity):
    """Command line interface pp-strong.
    
    postprocess a strong scaling test
    """

    of.pp_strong(case=case, location=location)    

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
#eodf
