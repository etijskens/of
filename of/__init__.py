# -*- coding: utf-8 -*-

"""
Package of
=======================================

On hortense need

    module load SciPy-bundle
    module load matplotlib

On Vaughan 

    module load Python
"""
import os, sys, re, subprocess, shutil, math
from typing import Union
from pathlib import Path
from collections import namedtuple
import io

try:
    import numpy as np
    from matplotlib import pyplot
except ModuleNotFoundError as x:
    print(x)
    print("Modules Numpy and matplotlib are needed for post-processing only.")
    print("On dodrio, run `module load SciPy-bundle` and `module load matplotlib`")

import click

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
                 , 'vsc-mympirun'
                 ]     
}

VSC_INSTITUTE_CLUSTER = os.environ['VSC_INSTITUTE_CLUSTER']
if VSC_INSTITUTE_CLUSTER not in NCORESPERNODE:
    raise NotImplementedError(f"Unknown cluster: VSC_INSTITUTE_CLUSTER = '{VSC_INSTITUTE_CLUSTER}'")


#===================================================================================================
def walltime_fmtd(value: Union[int,float,str]):
    """Convert hours to slurm wall time format HH:MM:SS

    :param float hours: walltime in hours.
    """
    if isinstance(value, str):
        return value
    else:
        # value is number of hours
        hh = int(value)
        minutes = (value - hh) * 60
        mm = int(minutes)
        ss = int((minutes - mm) * 60)
        s = f"{hh}:{mm:02}:{ss:02}"
        return s


#===================================================================================================
def jobscript(
      n_nodes: int
    , n_tasks: int
    , max_tasks_per_node: int
    , walltime: float
    , case_name: str
    , openfoam_solver: str
    , verbosity: int
    ):
    
    # is this job using the rquested nodes partially (i.e. less tasks per node than cores available per node)?
    partial_nodes = max_tasks_per_node != NCORESPERNODE[VSC_INSTITUTE_CLUSTER] \
                 or n_tasks < NCORESPERNODE[VSC_INSTITUTE_CLUSTER]
    
    script =  [ "#!/bin/bash"
              ,f"#SBATCH --nodes={n_nodes} --exclusive"
              ,f"#SBATCH --time={walltime_fmtd(walltime)}"
              ,f"#SBATCH --job-name={case_name}"
              , "#SBATCH -o %x.stdout"
              , "#SBATCH -e %x.stderr"
              ]
    if VSC_INSTITUTE_CLUSTER == 'dodrio':
        script += [
                "#SBATCH --account=astaff"
              , ""
              , "unset SLURM_EXPORT_ENV"
              , 'echo "JOB ID = $SLURM_JOB_ID"'
              ]
    script += [ ""
              , "module --force purge"
    ]
    # specify which modules to load
    for m in MODULES[VSC_INSTITUTE_CLUSTER]:
        script.append(f'module load {m}')
        
    script += [ "module list"
              , ""
              , "# Prepare OpenFOAM environment"
              , "source $FOAM_BASH"
              , ""
              ]

    script.append("# Preprocessing")
    if VSC_INSTITUTE_CLUSTER == 'dodrio':
        # blockMesh couldn't run in a single process on dodrio and should be run beforehand
        blockMesh = "# blockMesh # (pre-processing already done)"
    else:
        blockMesh = "blockMesh"
    script.append(f"{blockMesh}")

    if n_tasks == 1:
        script += [ "renumberMesh -overwrite"
                  , "# Processing"
                  ,f"{openfoam_solver} >& {case_name}.log"
                  ]
    else:
        if VSC_INSTITUTE_CLUSTER == 'dodrio':
            # --hybrid is way faster than --universe for partial nodes. --hybrid implies 'spread' pinning on a node,
            # i.e. processes are as far away from each other as possible, whereas --universe implies 'compact' pinning,
            # i.e. processes are as close together as possible.
            # the difference is large: for 1x16 cores --universe 16 takes 93.1s per timestep as opposed o 2.87s for 
            # --hybrid 16 (case = hpc/microbenchmarks/cavity-3d/8M/fixedIter)
            if partial_nodes:
                mpi_driver = f"mympirun --hybrid {min(max_tasks_per_node, n_tasks)}"
            else:
                mpi_driver = f"mympirun --universe {n_tasks}"
        else:
            mpi_driver = f"srun -np {n_tasks}"
            
        script += [f"foamDictionary -entry numberOfSubdomains -set {n_tasks} system/decomposeParDict"
                  , "rm -rf processor*"
                  , "decomposePar"
                  ,f"{mpi_driver} renumberMesh -parallel -overwrite"
                  , "# Processing"
                  ,f"{mpi_driver} {openfoam_solver} -parallel >& {case_name}.log"
                  ]

    script = '\n'.join(script)
    
    if verbosity > 3:
        print(80*'<')
        print(script)
        print(80*'>')
        
    return script


#===================================================================================================
def run_all( case:str
        , openfoam_solver:str         
        , destination:str = ''
        , postfix=''
        , max_nodes:int = 1
        , max_cores_per_node = NCORESPERNODE[VSC_INSTITUTE_CLUSTER]
        , walltime: float = 1
        , overwrite:bool = False
        , submit: bool = False
        , verbosity:bool = 0
    ):
    if not case:
        case = Path('.').resolve()
    else:
        case = Path(case)
    if not case.exists():
        raise FileNotFoundError(f"Missing OpenFOAM case folder '{case}'.")
    case_name = case.name
     
    if not destination:
        destination = Path(case).parent / f"{case_name}-strong-scaling-test-{NCORESPERNODE[VSC_INSTITUTE_CLUSTER]}.{max_cores_per_node}"
        os.makedirs(destination, exist_ok=True) # just in case this didn't already exist
    else:
        destination = Path(destination)
        if not case_path.exists():
            raise FileNotFoundError(f"Missing OpenFOAM case folder '{case}'.")
        
    if verbosity>2:
        print(f"{case=}\n{destination=}\n{openfoam_solver=}\n{max_nodes=}\n{max_cores_per_node=}\n{walltime=}\n{overwrite=}\n{submit=}\n{verbosity=}")
        if verbosity>=5:
            print("\nexiting because verbosity >= 5.")
            return

    n_nodes = [1]
    n_tasks = [ max_cores_per_node ]
    # single node jobs
    while n_tasks[0] != 1:
        n_tasks.insert(0, n_tasks[0] // 2)
        n_nodes.insert(0, 1)
    # multi-node jobs
    while n_nodes[-1] < max_nodes:
        n_nodes.append(n_nodes[-1] * 2)
        n_tasks.append(n_tasks[-1] * 2)
        
    if verbosity >= 4:
        print(f"{n_nodes=}")
        print(f"{n_tasks=}")
        
    for nn, nt in zip(n_nodes, n_tasks):
        # print(nn,nt)
        run1(
            case=case
          , openfoam_solver=openfoam_solver
          , destination=destination
          , n_nodes = nn
          , n_tasks = nt
          , max_tasks_per_node = max_cores_per_node
          , walltime = walltime
          , overwrite = overwrite
          , submit = submit
          , verbosity = verbosity
        )
#===================================================================================================
def run1( case
        , openfoam_solver
        , destination
        , n_nodes
        , n_tasks
        , max_tasks_per_node
        , walltime
        , overwrite
        , submit
        , verbosity
    ):
    """Create and run an OpenFOAM case on n_nodes nodes with n_tasks MPI tasks.

    Copy an OpenFOAM case and run it with a number of nodes or cores for performance evaluation.
    Create and submit job.
    
    :param case: path to existing OpenFOAM case
    :param openfoam_solver: name of the solver used in the simulation. (Should be on the PATH).
    :param destination: path where the case will be copied to
    :param n_nodes: the number of nodes requested
    :param n_tasks: the total number of mpi tasks that will be started
    :param max_tasks_per_node: maximum number of mpi tasks per node that will be started
    :param walltime: the walltime requested, either a positive number or a 'HH:MM:SS' str.
    :param overwrite: if True, and the case directory already exists in the destination, the case will be
        removed and recreated (previous results will be lost).
    :param submit: if True the job script will be submitted.
    :param verbosity: print more output, 

    """    
    
    if VSC_INSTITUTE_CLUSTER == 'dodrio':
        # Verify that blockMesh has been run in the case directory.
        p = case / 'constant/polyMesh/points'
        if not p.exists():
            raise RuntimeError("You must run blockMesh in the case directory.")

    run_case_name = f"{case.name}-{n_nodes}x{n_tasks//n_nodes}cores"
    run_case = destination / run_case_name
    click.echo('\nPreparing case for for {VSC_INSTITUTE_CLUSTER}:\n  ' + click.style(f"{run_case}", fg='green'))

    if overwrite:
        shutil.rmtree(run_case, ignore_errors=True)
    
    run_case_jobscript_path = run_case / f'{run_case_name}.slurm'
    if not run_case.exists():
        # Copy the case
        shutil.copytree(case, run_case)

        # Create and write jobscript
        run_case_jobscript = jobscript( n_nodes=n_nodes
                                      , n_tasks=n_tasks 
                                      , max_tasks_per_node=max_tasks_per_node
                                      , walltime=walltime
                                      , case_name=run_case_name
                                      , openfoam_solver=openfoam_solver
                                      , verbosity=verbosity
                                      )
        with open( run_case_jobscript_path, mode='w') as f:
            f.write(run_case_jobscript)
            if verbosity > 1:
                click.echo('  Jobscript written.')

    else:
        click.secho(f"Folder '{run_case}' already exists. (Specify overwrite=True to remove and recreate it)", fg='blue')        
        
    # Submit the job if submit==True and the case directory does not have a .log file.
    case_log_path = run_case / f'{run_case_name}.log'
    if submit and not case_log_path.exists():
        cmd = ['sbatch', run_case_jobscript_path.name]
        print(f'  > {" ".join(cmd)}')
        subprocess.run(cmd, cwd=run_case)
        click.secho("  Submitted.", fg='green')
    else:
        msg = "  NOT submitted: "
        if case_log_path.exists():
            msg += 'log-file already exists.'
        else:
            msg += "'--submit' not specified."
        click.secho(msg, fg='red')
            

#===================================================================================================
def get_mean_walltime_per_timestep(file):
    # print(f"{file=}")
    if file.is_dir():
        file = file / (file.name + '.log')
    
    if not file.exists():
        click.secho(f".log file '{file}' not found. Ignoring it.", fg='red')
        return float('NAN')
    
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
    """Read the number of cells from the output. 

    we are looking for line "Mesh region0 size: 8000000".
    (The original approach looked for "nCells:" in the blockMesh output. )
    """
    if file.is_dir():
        file = file / (file.name + '.stdout')
    if not file.exists():
        click.secho(f".stdout file '{file}' not found. Ignoring it.", fg='red')
        return float('NAN')
    
    with open(file) as f:
         for line in f:
            match = re.match(r'Mesh (\w+) size: (\d+)', line)
            if match:
                ncells = int(match.group(2))
                return ncells 
            match = re.match(r'Mesh size: (\d+)', line)
            if match:
                ncells = int(match.group(1))
                return ncells 



#===================================================================================================
def postprocess( case, results, verbosity):
    """Postprocess strong scaling test results.
    """
       
    try:
        np      
    except NameError:
        print('Numpy must be available for post-processing.')
        sys.exit(1)
    
    results = Path(results).resolve()
    if not case:
        results_name = results.name
        pattern = r"(\w+)-strong-scaling-test"
        m = re.match(pattern, results_name)
        if m:
            case = m[1]
        else:
            raise ValueError(f"Unable to extract case name from results directory {results}")
    
    if verbosity:
        print(f"{case=}")
        
    if not results.exists():
        raise FileNotFoundError(results)
    
    # Pick up the case directories.
    s = r'(\w+)-(\d+)x(\d+)cores'
    cases = {}
    n_cores = []
    Dir = namedtuple('Dir', ['name', 'n_nodes', 'n_tasks'])
    for item in results.glob('*'):
        if item.is_dir():
            m = re.match(s, str(item.name))
            if m:
                case = m[1]
                if not case in cases:
                    cases[case] = []
                cases[case].append(Dir( item.name, int(m[2]),  int(m[2]) * int(m[3]) ))

    if verbosity:
       print(f"{cases=}")
    
    for case, dirs in cases.items():
        n_nodes = np.array([dir.n_nodes for dir in dirs])
        n_cores = np.array([dir.n_tasks for dir in dirs])
        
        dirs = np.array([dir.name for dir in dirs])
        p = n_cores.argsort()
        n_nodes = n_nodes[p]
        n_cores = n_cores[p]
        dirs = dirs[p]
        
        walltimes = []
        n_cells = []
        for dir in dirs:
            # print(f"{dir=}")
            pdir = results / dir
            walltimes.append(get_mean_walltime_per_timestep(pdir))
            n_cells.append(get_ncells(pdir))
        n_cells = np.array(n_cells)
        walltimes = np.array(walltimes)
        cpu_times = walltimes * n_cores
        cells_per_core = n_cells / n_cores
        speedup = walltimes[0]/walltimes
        parallel_efficiency = speedup/n_cores
        
        d = {            
            '# nodes' : n_nodes
          , '# cores' : n_cores
          , 'walltime per timestep' : walltimes
          , 'cpu_time per timestep' : cpu_times
          , 'cells per core' : cells_per_core
          , 'speedup' : speedup
          , 'parallel efficiency' : parallel_efficiency
        }
    
    # print to string
    output = io.StringIO()
    line = 69*'-'
    print(line, file=output)
    title = f"Case {case} (on {VSC_INSTITUTE_CLUSTER})"
    print(f"{title:^69}", file=output)
    print(line, file=output)
    print(f"{     ' ':>10}{     ' ':>10}{'walltime':>10}{'cpu_time':>10}{'#cells':>10}{      ' ':>8}{         ' ':>11}"  , file=output)
    print(f"{     ' ':>10}{     ' ':>10}{     'per':>10}{     'per':>10}{   'per':>10}{      ' ':>8}{  'parallel':>11}"  , file=output)
    print(f"{'#nodes':>10}{'#cores':>10}{'timestep':>10}{'timestep':>10}{  'core':>10}{'speedup':>8}{'efficiency':>11}\n", file=output)
    for i in range(len(n_cores)):
        print(f"{n_nodes[i]:>10}{n_cores[i]:>10}{walltimes[i]:>10.3f}{cpu_times[i]:>10.3f}{cells_per_core[i]:>10.0f}{speedup[i]:>8.1f}{parallel_efficiency[i]:>11.3f}", file=output)
    print(line, file=output)
    
    # print to stdout
    print()
    print(output.getvalue())
    
    # print to file
    with open(results / (case + ".parallel_efficiency.txt"), mode='w') as f:
        print(output.getvalue(), file=f)
    
    # Produce plot and save .png
    try:
        pyplot
    except NameError:
        print('Matplotlib must be available for further post-processing.')
        sys.exit(1)
    
    fig = pyplot.figure()
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twiny()
    
    ax1.plot(n_cores, parallel_efficiency, 'o-')
    ax1.set_title(title)
    ax1.set_xlabel('# cores')
    ax1.set_ylabel('parallel efficiency')
    # ax1.set_axis([0, n_cores[-1], 0, 1])
    ax1.set_xscale('log')
    ax2_tick_resultss = n_cores

    def tick_function(ncores):
        labels = []
        for i in range(len(ncores)):
            label = f'{ncores[i]}'
            labels.append(label)
        return labels

    ax2.set_xscale('log')
    ax2.set_xlim(ax1.get_xlim())
    ax2.set_xticks(ax2_tick_resultss)
    ax2.set_xticklabels(tick_function(ax2_tick_resultss))
    
    for i in range(len(cells_per_core)):
        ax2.plot( [n_cores[i], n_cores[i]], [0,1])
        if math.isnan(cells_per_core[i]):
            cpc = "NAN" 
        else:
            cpc = int(cells_per_core[i])
        pyplot.text(n_cores[i],0,f'{cpc} cells/core', rotation=90)
    
    pyplot.savefig(str(results / (case + ".parallel_efficiency.png")), dpi=200)
    pyplot.show()

    return d
    
    
#===================================================================================================
# code below just for quick testing

if __name__ == "__main__":
    pp = True

    if VSC_INSTITUTE_CLUSTER == 'dodrio':
        case = '/dodrio/scratch/users/vsc20170/prj-astaff/vsc20170/exafoam/hpc/microbenchmarks/cavity-3d/8M/fixedIter'
    elif VSC_INSTITUTE_CLUSTER == 'vaughan':
        case = '/user/antwerpen/201/vsc20170/scratch/workspace/exafoam/hpc/microbenchmarks/cavity-3d/8M/fixedIter'
    case_path = Path(case) 
    dest_path = (Path(case) / '..' / f'{case_path.name}-strong-scaling-test')

    if pp:
        postprocess(dest_path)
    else:
        run_all( case=case_path
        , destination = dest_path
        , openfoam_solver = 'icoFoam'     
        , max_nodes = 4
        , walltime = 1
        , overwrite = True
        , submit = True
        , verbosity = 2
        )
    print("-*# finished #*-")