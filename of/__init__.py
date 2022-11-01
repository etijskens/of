# -*- coding: utf-8 -*-

"""
Package of
=======================================

Top-level package for of.
"""
import os
from pydoc import cli
import click
from pathlib import Path
import subprocess
import shutil

__version__ = "0.1.4"

NCORESPERNODE = {
    'leibniz' :  28
  , 'vaughan' :  64
  , 'hortense': 128
}

def walltimeStr(hours):
    """Convert hours to slurm wall time format HH:MM:SS

    :param float hours: walltime in hours.
    """
    hh = int(hours)
    minutes = (hours - hh) * 60
    mm = int(minutes)
    ss = int((minutes - mm) * 60)
    s = f"{hh}:{mm:02}:{ss:02}"
    return s

def jobscript(nNodes, nCores, walltime, case_name, openfoam_solver):
    script = """#!/bin/bash
#SBATCH --nodes={nNodes} --exclusive
#SBATCH --time={walltime}
#SBATCH --job-name={case_name}
#SBATCH -o %x.%j.stdout
#SBATCH -e %x.%j.stderr

# Prepare OpenFOAM environment
module --force purge
module load vaughan/2020a
module load OpenFOAM/8-intel-2020a
module list
source $FOAM_BASH

# Preprocessing
blockMesh
"""
    if nCores == 1:
        script += """renumberMesh -overwrite

# Processing
{openfoam_solver} >& {case_name}.log
"""
    else:
        script += """rm -rf processor*
foamDictionary -entry numberOfSubdomains -set {nCores} system/decomposeParDict
decomposePar
mpirun -np {nCores} renumberMesh -parallel -overwrite

# Processing
mpirun -np {nCores} {openfoam_solver} -parallel >& {case_name}.log"""
    # print(script)
    return script.format(nNodes=nNodes, nCores=nCores, walltime=walltime, case_name=case_name, openfoam_solver=openfoam_solver)


def run( case
       , destination=''
       , ncores=1, nnodes=1
       , walltime=1
       , overwrite=False
       , submit=False
       , verbosity=0
       ):
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
        nCoresPerNode = NCORESPERNODE[cluster] if nNodes > 1 else ncores

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
    else:
        if dest_path.exists():
            click.secho(f"{dest_path} already exists.", fg='blue')
            return
        
    shutil.copytree(case_path, dest_path)

    # jobscript
    job_script = jobscript(
        nNodes=nNodes
      , nCores=nCores
      , walltime=walltimeStr(walltime)
      , case_name=case_name
      , openfoam_solver='icoFoam'
    )
    script_path = dest_path / f'{case_name}.slurm'
    if verbosity > 1:
        line = 80 * '-'
        print(line)
        click.echo('jobscript = ' + click.style(f"{script_path}", fg='green'))
        print(line)
        click.secho(job_script, fg='green')
        print(line)
    with open( script_path, mode='w') as f:
        f.write(job_script)

    if submit:
        cmd = ['sbatch', script_path.name]
        print(f'  > {" ".join(cmd)}')
        subprocess.run(cmd, cwd=dest_path)
        click.echo(click.style(f"Job script '{script_path}' submitted in directory '{dest_path}'.", fg='green'))
    else:
        click.echo(click.style(f"Job script '{script_path}' not submitted.", fg='red'))
