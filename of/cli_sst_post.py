# -*- coding: utf-8 -*-
"""Command line interface pp-strong (no sub-commands)."""
# -*- coding: utf-8 -*-
"""Command line interface sst-post (no sub-commands)."""

import sys

try:
    import of
except ModuleNotFoundError:
    # pick up the path from __file__
    from pathlib import Path
    p = str(Path(__file__).parent.parent)
    sys.path.insert(0,p)
    import of
    # for sp in sys.path:
    #     print(f"{sp=}")

import click

@click.command()
@click.option('--case', '-c', default=''
             , help='name of the OpenFOAM case directory. If not provided, '
                    'an attempt is made to extract it from the results directory.'
             )
@click.option('--results', '-r', default='.'
             , help='Directory containing the results of the scaling test.'
             )
@click.option('--clean/--no-clean', is_flag=True, default=True
             , help='Remove processor* directories to free disk space. Default is True.'
             )
@click.option('--verbosity', '-v', count=True, default=0
             , help="The verbosity of the program."
             )
def main(case, results, clean, verbosity):
    """Command line interface sst_post.
    
    Post-process a strong scaling test.
    """

    of.postprocess(case=case, results=results, clean=clean, verbosity=verbosity)    

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
#eodf
