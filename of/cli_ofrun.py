# -*- coding: utf-8 -*-
"""Command line interface ofrun (no sub-commands)."""

import sys,os
sys.path.insert(0,'.')

import click
from pathlib import Path
import shutil

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
@click.option('-v', '--verbosity', count=True
             , help="The verbosity of the program."
             , default=0
             )
def main( case, destination
        , ncores, nnodes
        , verbosity):
    """Command line interface ofrun.

    Copy an OpenFOAM case and run it with a number of nodes or cores for performance evaluation
    """

    #  verify that case path exists
    case_path = Path(case)
    if not case_path.exists():
        raise FileNotFoundError(case)

    if verbosity:
        click.echo('case = '+click.style(f"{case}", fg='green'))

    # determine destination path and verify
    dest_path = case_path.parent if not destination else Path(destination)
    if not dest_path.exists():
        raise FileNotFoundError(dest_path)

    if verbosity:
        click.echo('dest = '+click.style(f"{dest_path}", fg='green'))

    cluster = os.environ['VSC_INSTITUTE_CLUSTER']
    if cluster in ('local',''):
        cluster = 'local-machine'
        nnodes = 1
        nCoresPerNode = ncores
    else:
        nCoresPerNode = of.nCoresPerNode[cluster] if nnodes > 1 else ncores

    ncores = nCoresPerNode * nnodes

    if verbosity:
        click.echo('cluster = ' + click.style(f"{cluster}", fg='green'))
        click.echo('nnodes  = ' + click.style(f"{nnodes}", fg='green'))
        click.echo('corespn = ' + click.style(f"{nCoresPerNode}", fg='green'))
        click.echo('ncores  = ' + click.style(f"{ncores}", fg='green'))

    case_name = case_path.name+'-{}x{}cores'.format(nnodes, nCoresPerNode)
    if verbosity:
        click.echo('case_name = ' + click.style(f"{case_name}", fg='green'))

    dest_path = dest_path / case_name

    shutil.copytree(case_path, dest_path)

if __name__ == "__main__":


    sys.exit(main())  # pragma: no cover
#eof
