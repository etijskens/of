# -*- coding: utf-8 -*-
"""Command line interface ofrun (no sub-commands)."""

import sys,os
sys.path.insert(0,'.')

import click

import of

@click.command()
@click.option('-c','--case'
             , help='Location of the original OpenFOAM case, absolute path or relative to pwd.'
             )
@click.option('-d','--destination'
             , help='Location where case is copied to. Default is the parent of the --case directory'
             , default=''
             )
@click.option('--ncores'
             , help='number of cores requested on a single node. Sets nnodes to 1.'
             , default=1
             )
@click.option('--nnodes'
             , help='number of nodes requested. Sets ncores to the maximum number of physical cores on a node.'
             , default=1
             )
@click.option('-w', '--walltime'
             , help='walltime limit of the job.'
             , default=1
             )
@click.option('-o', '--overwrite'
             , help='overwrite the case directory if it already exists.'
             , is_flag=True, default=False
             )
@click.option('-s', '--submit'
             , help='submit the job.'
             , is_flag=True, default=False
             )
@click.option('-v', '--verbosity', count=True
             , help="The verbosity of the program."
             , default=0
             )
def main( case, destination
        , ncores, nnodes
        , walltime
        , overwrite
        , submit
        , verbosity):
    """Command line interface ofrun.

    Copy an OpenFOAM case and run it with a number of nodes or cores for performance evaluation.
    Create and submit job.
    """
    of.ofrun( case, destination
            , ncores, nnodes
            , walltime
            , overwrite
            , submit
            , verbosity
            )


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
#eof
