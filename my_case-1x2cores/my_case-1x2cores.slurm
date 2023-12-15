#!/bin/bash
#SBATCH --nodes=1 --exclusive
#SBATCH --time=1:00:00
#SBATCH --job-name=my_case-1x2cores
#SBATCH -o %x.%j.stdout
#SBATCH -e %x.%j.stderr

# Prepare OpenFOAM environment
module --force purge
module load vaughan/2020a
module load OpenFOAM/8-intel-2020a
module list
source $FOAM_BASH

# Preprocessing
blockMeshrm -rf processor*
foamDictionary -entry numberOfSubdomains -set 2 system/decomposeParDict
decomposePar
mpirun -np 2 renumberMesh -parallel -overwrite

# Processing
mpirun -np 2 icoFoam -parallel >& my_case-1x2cores.log