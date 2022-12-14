# -*- coding: utf-8 -*-
"""Command line interface sst-run (no sub-commands)."""

import sys

try:
    import of
except ModuleNotFoundError:
    # pick up the path from __file__
    from pathlib import Path
    p = str(Path(__file__).parent.parent)
    sys.path.insert(0,p)
    # for sp in sys.path:
    #     print(f"{sp=}")
    import of

import click

@click.command()
@click.option('--case', '-c', default=''
             , help='Location of the original OpenFOAM case, absolute path or relative to pwd. '
                    'The default is the current directory.'
             )
@click.option('--solver', '-s', default='icoFoam' 
             , help='OpenFOAM solver to be used.'
             )
@click.option('--destination', '-d', default=''
             , help="Location where case is copied to. Default is the parent of the --case directory, "
                    "in which case the directory is named '{case.name}-strong-scaling-test[-{postfix}]'."
             )
@click.option('--max-nodes', '-n', default=1
             , help='maximum number of nodes requested. Job are created for 1 node, 2 nodes, 4 nodes, ... '
                    'Single node jobs are also created with nc cores, nc/2 cores, nc/4 cores, ..., 1 core, '
                    'where nc is the number of cores on a node.'
             )
@click.option('--max-cores', '-c', default=of.NCORESPERNODE[of.VSC_INSTITUTE_CLUSTER]
             , help='maximum number of cores per node allowed. This option allows to use not fully occupied nodes.'
             )
@click.option('--walltime', '-w', default=1
             , help='walltime limit of the job. Format is hh:mm:ss or a number of hours.'
             )
@click.option('--overwrite', is_flag=True, default=False
             , help='Overwrite the case directory if it already exists. Note, that this option removes '
                    'previous results. Hence, the command must be run (or rerun) with the --submit flag.'
             )
@click.option('--submit/--no-submit', is_flag=True, default=False
             , help='If True, submit all cases that have no .log file. This includes newly created cases, '
                    'overwritten cases and cases for which the log file has been deleted manually.'
             )
@click.option('--verbosity', '-v', count=True, default=0
             , help="The verbosity of the program."
             )
def main( case, destination, solver
        , max_nodes, max_cores, walltime
        , overwrite, submit
        , verbosity
    ):
    """Command line interface run-sst.

    Copy an OpenFOAM case and perform a (strong) scaling test.
    """
    of.run_all( case=case, openfoam_solver=solver, destination=destination
              , max_nodes=max_nodes, max_cores_per_node=max_cores, walltime=walltime
              , overwrite=overwrite, submit=submit
              , verbosity=verbosity
              )

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
#eof
