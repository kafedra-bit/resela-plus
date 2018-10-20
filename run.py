#!/usr/bin/env python3

"""
Code for running Resela from the command-line interface.
"""

from sys import argv, exit

import logging
from argparse import ArgumentParser

from resela.app import APP, app_init, write_default_config, DATABASE
from resela.backend.SqlOrm.DefaultOS import fill_database_default

LOG = logging.getLogger(__name__)


def main(args):
    """Read the CLI arguments and run Resela accordingly.

    :param args: CLI arguments parsed by `argparse`.
    :type args: `argparse.Namespace`
    """

    if args.dump_config:
        write_default_config(dest='/dev/stdout')
        exit(0)

    app_init(args.config_path)

    if args.init_database:
        DATABASE.create_all()
        exit(0)

    if args.fill_database:
        DATABASE.create_all()
        fill_database_default()
        exit(0)

    APP.run()

if __name__ == '__main__':
    # Disable caching in devmode

    parser = ArgumentParser('Resela')
    parser.add_argument(
        '--dump-config',
        dest='dump_config',
        action='store_true',
        help='Print the default configuration.'
    )
    parser.add_argument(
        '-c',
        '--config',
        dest='config_path',
        metavar='CONFIG_FILE',
        default=None,
        help='Use a configuration other than the one at the default path.'
    )
    parser.add_argument(
        '--fill-database',
        dest='fill_database',
        action='store_true',
        help='Fills the database with default values for the search menu'
    )
    parser.add_argument(
        '--init-database',
        dest='init_database',
        action='store_true',
        help='Initializes the database used for the search menu.'
    )

    # Parse the CLI arguments to make them more manageable.
    args = parser.parse_args(argv[1:])
    main(args)

