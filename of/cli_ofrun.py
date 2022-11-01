# -*- coding: utf-8 -*-
"""Command line interface ofrun (no sub-commands)."""

import sys,os
sys.path.insert(0,'.')

import click
from pathlib import Path
import subprocess
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
        nNodes = 1
        nCoresPerNode = ncores
    else:
        nNodes = nnodes
        nCoresPerNode = of.nCoresPerNode[cluster] if nNodes > 1 else ncores

    nCores = nCoresPerNode * nnodes

    if verbosity:
        click.echo('cluster = ' + click.style(f"{cluster}", fg='green'))
        click.echo('nNodes  = ' + click.style(f"{nNodes}", fg='green'))
        click.echo('nCoresPerNode = ' + click.style(f"{nCoresPerNode}", fg='green'))
        click.echo('ncores  = ' + click.style(f"{nCores}", fg='green'))

    case_name = case_path.name+'-{}x{}cores'.format(nnodes, nCoresPerNode)
    dest_path = dest_path / case_name
    if verbosity:
        click.echo('case_name = ' + click.style(f"{case_name}", fg='green'))

    if overwrite:
        shutil.rmtree(dest_path, ignore_errors=True)
    shutil.copytree(case_path, dest_path)

    # jobscript
    jobscript = of.jobscript(
        nNodes=nNodes
      , nCores=nCores
      , walltime=of.walltime(walltime)
      , case_name=case_name
      , openfoam_solver='icoFoam'
    )
    script_path = dest_path / f'{case_name}.slurm'
    if verbosity > 1:
        line = 80 * '-'
        print(line)
        click.echo('jobscript = ' + click.style(f"{script_path}", fg='green'))
        print(line)
        click.secho(jobscript, fg='green')
        print(line)
    with open( script_path, mode='w') as f:
        f.write(jobscript)

    if submit:
        cmd = ['sbatch', script_path.name]
        print(f'  > {" ".join(cmd)}')
        subprocess.run(cmd, cwd=dest_path)
        click.echo(click.style(f"Job script '{script_path}' submitted in directory '{dest_path}'.", fg='green'))
    else:
        click.echo(click.style(f"Job script '{script_path}' not submitted.", fg='red'))


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
#eof
