# -*- coding: utf-8 -*-

"""
Package of
=======================================

On hortense need

    module load SciPy-bundle
    module load matplotlibm

On Vaughan 

    module load Python
"""
import os
import re
import click
from pathlib import Path
import subprocess
import shutil
import numpy as np
from matplotlib import pyplot

__version__ = "0.3.0"

#===================================================================================================
NCORESPERNODE = {
    'leibniz' :  28
  , 'vaughan' :  64
  , 'dodrio'  : 128
}

MODULES = {
    'leibniz' :  [ 'leibniz/supported'
                 , 'OpenFOAM/v2012-intel-2020a'
                 ]
  , 'vaughan' :  [ 'vaughan/2020a'
                 , 'OpenFOAM/v2012-intel-2020a'
                 ]
  , 'dodrio'  :  [ 'cluster/dodrio/cpu_rome'
                 , 'OpenFOAM/v2206-foss-2022a'
                 ]     
}

VSC_INSTITUTE_CLUSTER = os.environ['VSC_INSTITUTE_CLUSTER']
if VSC_INSTITUTE_CLUSTER not in NCORESPERNODE:
    raise NotImplementedError(f"Unknown cluster: VSC_INSTITUTE_CLUSTER = '{VSC_INSTITUTE_CLUSTER}'")


#===================================================================================================
def walltime_to_str(hours):
    """Convert hours to slurm wall time format HH:MM:SS

    :param float hours: walltime in hours.
    """
    hh = int(hours)
    minutes = (hours - hh) * 60
    mm = int(minutes)
    ss = int((minutes - mm) * 60)
    s = f"{hh}:{mm:02}:{ss:02}"
    return s


#===================================================================================================
def jobscript(
      n_nodes: int
    , n_tasks: int
    , walltime: float
    , case_name: str
    , openfoam_solver: str
    ):
    
    script = """#!/bin/bash
#SBATCH --nodes={n_nodes} --exclusive
#SBATCH --time={walltime}
#SBATCH --job-name={case_name}
#SBATCH -o %x.stdout
#SBATCH -e %x.stderr

# Prepare OpenFOAM environment
module --force purge
"""
    # specify which modules to load
    for m in MODULES[VSC_INSTITUTE_CLUSTER]:
        script += f'module load {m}\n'

    script += """
module list
source $FOAM_BASH

# Preprocessing
blockMesh
"""
    if n_tasks == 1:
        script += """renumberMesh -overwrite

# Processing
{openfoam_solver} >& {case_name}.log
"""
    else:
        script += """rm -rf processor*
foamDictionary -entry numberOfSubdomains -set {n_tasks} system/decomposeParDict
decomposePar
mpirun -np {n_tasks} renumberMesh -parallel -overwrite

# Processing
mpirun -np {n_tasks} {openfoam_solver} -parallel >& {case_name}.log"""
    # print(script)
    return script.format(n_nodes=n_nodes, n_tasks=n_tasks, walltime=walltime, case_name=case_name, openfoam_solver=openfoam_solver)


#===================================================================================================
def run_all( case:str
        , openfoam_solver:str         
        , destination:str = ''
        , max_nodes:int = 1
        , walltime: float = 1
        , overwrite:bool = False
        , submit: bool = False
        , verbosity:bool = 0
    ):
    n_nodes = [1]
    n_tasks = [NCORESPERNODE[VSC_INSTITUTE_CLUSTER]]
    while n_tasks[0] != 1:
        n_tasks.insert(0, n_tasks[0] // 2)
        n_nodes.insert(0, 1)
    while n_nodes[-1] < max_nodes:
        n_nodes.append(n_nodes[-1] * 2)
        n_tasks.append(n_tasks[-1] * 2)
    print(n_nodes)
    print(n_tasks)
        
    for nn, nt in zip(n_nodes, n_tasks):
        print(nn,nt)
        run1(
            case=case
          , openfoam_solver=openfoam_solver
          , destination=destination
          , n_nodes = nn
          , n_tasks = nt
          , walltime = walltime
          , overwrite = overwrite
          , submit = submit
          , verbosity = verbosity
        )
#===================================================================================================
def run1( case:str
        , openfoam_solver:str         
        , destination:str = ''
        , n_nodes:int = 1
        , n_tasks:int = 1
        , walltime: float = 1
        , overwrite:bool = False
        , submit: bool = False
        , verbosity:bool = 0
    ):
    """Create and run an OpenFOAM case on n_nodes nodes with n_tasks MPI tasks.

    Copy an OpenFOAM case and run it with a number of nodes or cores for performance evaluation.
    Create and submit job.
    
    :param case: path to existing OpenFOAM case
    :param openfoam_solver: name of the solver used in the simulation. (Should be on the PATH).
    :param destination: path where the case will be copied to
    :param n_nodes: the number of nodes requested
    :param n_tasks: the number of mpi tasks that will be started
    :param walltime: the walltime requested
    :param overwrite: if True, and the case directory already exists in the destination, the case will be
        removed and recreated (previous results will be lost).
    :param submit: if True the job script will be submitted.
    :param verbosity: print more output, 

    """
    #  verify that case path exists
    case_path = Path(case)
    if not case_path.exists():
        raise FileNotFoundError(f"Missing OpenFOAM '{case}'.")

    # determine destination path and verify
    dest_path = case_path.parent if not destination else Path(destination)
    if not dest_path.exists():
        raise FileNotFoundError(dest_path)

    case_name = case_path.name+'-{}x{}cores'.format(n_nodes, n_tasks if n_nodes == 1 else NCORESPERNODE[VSC_INSTITUTE_CLUSTER])

    dest_path = dest_path / case_name
    click.echo('\nPreparing case ' + click.style(f"{dest_path}", fg='green'))

    if verbosity:
        click.echo('case = '+click.style(f"{case}", fg='green'))
        click.echo('dest = '+click.style(f"{dest_path}", fg='green'))
        click.echo('cluster          = ' + click.style(f"{VSC_INSTITUTE_CLUSTER}", fg='green'))
        click.echo('# nodes          = ' + click.style(f"{n_nodes}", fg='green'))
        click.echo('# cores per node = ' + click.style(f"{NCORESPERNODE[VSC_INSTITUTE_CLUSTER]}", fg='green'))
        click.echo('# mpi tasks      = ' + click.style(f"{n_tasks}", fg='green'))

    if overwrite:
        shutil.rmtree(dest_path, ignore_errors=True)
    else:
        if dest_path.exists():
            click.secho(f"destination '{dest_path}' already exists. (Specify overwrite=True to remove and recreate it)", fg='blue')
            return
        
    shutil.copytree(case_path, dest_path)

    # jobscript
    job_script = jobscript(
        n_nodes=n_nodes
      , n_tasks=n_tasks
      , walltime=walltime
      , case_name=case_name
      , openfoam_solver=openfoam_solver
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


#===================================================================================================
def get_mean_walltime_per_timestep(file):
    if file.is_dir():
        file = file / (file.name + '.log')
    
    with open(file) as f:
        ExecutionTimes = []
        for line in f:
            match = re.match(r'ExecutionTime = (\d+(\.\d*)?)', line)
            if match:
                w = float(match.group(1))
                # print(f"    walltime = {w}")
                ExecutionTimes.append(w)
                # print(ExecutionTimes)
        ExecutionTimes = np.array(ExecutionTimes)
        # OpenFOAM's ExecutionTime is the elapsed time since the start.
        # Hence, we need to diff and average 
        time_per_timestep = np.diff(ExecutionTimes)
        # print(time_per_timestep)
        mean_walltime_per_timestep = np.mean(time_per_timestep) 
        # print(mean_walltime_per_timestep)
    return mean_walltime_per_timestep


#===================================================================================================
def get_ncells(file):
    """Read the number of cells from the OpenFOAM output"""
    if file.is_dir():
        file = file / (file.name + '.stdout')
    with open(file) as f:
         for line in f:
            match = re.match(r'  nCells: (\d+)', line)
            if match:
                ncells = int(match.group(1))
                return ncells       


#===================================================================================================
def pp_strong(case, location='.', verbosity=0):
    """Postprocess strong scaling test results.
    
    :param str case: name of the case directory
    :param str|Path location: parent directory containing the results
    """
    location = Path(location)
    if not location.exists():
        raise FileNotFoundError(location)
    
    s = case + r'-(\d+)x(\d+)cores'
    dirs = []
    n_cores = []
    for item in location.glob('*'):
        if item.is_dir():
            m = re.match(s, str(item.name))
            if m:
                n = int(m[1]) * int(m[2])
                n_cores.append(n)
                dirs.append(item)
    n_cores = np.array(n_cores)
    p = n_cores.argsort()
    n_cores = n_cores[p]
    dirs = np.array(dirs)[p]
    walltimes = []
    n_cells = []
    for dir in dirs:
        walltimes.append(get_mean_walltime_per_timestep(dir))
        n_cells.append(get_ncells(dir))
    n_cells = np.array(n_cells)
    walltimes = np.array(walltimes)
    cpu_times = walltimes * n_cores
    cells_per_core = n_cells / n_cores
    speedup = walltimes[0]/walltimes
    parallel_efficiency = speedup/n_cores
    
    d = {
        '# cores' : n_cores
      , 'walltime per timestep' : walltimes
      , 'cpu_time per timestep' : cpu_times
      , 'cells per core' : cells_per_core
      , 'speedup' : speedup
      , 'parallel efficiency' : parallel_efficiency
    }
    
    print()
    print(f"{     ' ':>10}{'walltime':>10}{'cpu_time':>10}{'#cells':>10}{      ' ':>8}{         ' ':>11}")
    print(f"{     ' ':>10}{     'per':>10}{     'per':>10}{   'per':>10}{      ' ':>8}{  'parallel':>11}")
    print(f"{'#cores':>10}{'timestep':>10}{'timestep':>10}{  'core':>10}{'speedup':>8}{'efficiency':>11}")
    print()
    for i in range(len(n_cores)):
        print(f"{n_cores[i]:>10}{walltimes[i]:>10.3f}{cpu_times[i]:>10.3f}{cells_per_core[i]:>10.0f}{speedup[i]:>8.1f}{parallel_efficiency[i]:>11.3f}")
    
    # Produce plot and save .png
    fig = pyplot.figure()
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twiny()
    
    ax1.plot(n_cores, parallel_efficiency, 'o-')
    ax1.set_title(case)
    ax1.set_xlabel('# cores')
    ax1.set_ylabel('parallel efficiency')
    # ax1.set_axis([0, n_cores[-1], 0, 1])
    ax1.set_xscale('log')
    ax2_tick_locations = n_cores

    def tick_function(ncores):
        labels = []
        for i in range(len(ncores)):
            label = f'{ncores[i]}'
            labels.append(label)
        return labels

    ax2.set_xscale('log')
    ax2.set_xlim(ax1.get_xlim())
    ax2.set_xticks(ax2_tick_locations)
    ax2.set_xticklabels(tick_function(ax2_tick_locations))
    
    for i in range(len(cells_per_core)):
        ax2.plot( [n_cores[i], n_cores[i]], [0,1])
        pyplot.text(n_cores[i],0,f'{int(cells_per_core[i])} cells/core', rotation=90)
    
    pyplot.savefig(str(location / (case + ".parallel_efficiency.png")), dpi=200)
    pyplot.show()

    return d
    
    
#===================================================================================================
if __name__ == "__main__":
    if VSC_INSTITUTE_CLUSTER == 'dodrio':
        case = '/dodrio/scratch/users/vsc20170/prj-astaff/vsc20170/hpc/microbenchmarks/cavity-3d/8M/fixedIter'
    elif VSC_INSTITUTE_CLUSTER == 'vaughan':
        case = '/user/antwerpen/201/vsc20170/scratch/workspace/exafoam/hpc/microbenchmarks/cavity-3d/8M/fixedIter'
    run_all( case=case
      , openfoam_solver = 'icoFoam'     
      , max_nodes = 4
      , walltime = 1
      , overwrite = True
      , submit = False
      , verbosity = 2
    )
    # postprocess(case='fixedIter', location='/user/antwerpen/201/vsc20170/scratch/workspace/exafoam/hpc/microbenchmarks/cavity-3d/1M')
    print("-*# finished #*-")