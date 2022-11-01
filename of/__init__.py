# -*- coding: utf-8 -*-

"""
Package of
=======================================

Top-level package for of.
"""

import of.cli_ofrun
__version__ = "0.1.1"

nCoresPerNode = {
    'leibniz' :  28
  , 'vaughan' :  64
  , 'hortense': 128
}

def walltime(hours):
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
mpirun -np {nCores} icoFoam -parallel >& {case_name}.log"""
    # print(script)
    return script.format(nNodes=nNodes, nCores=nCores, walltime=walltime, case_name=case_name, openfoam_solver=openfoam_solver)