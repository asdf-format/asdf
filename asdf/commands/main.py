# -*- coding: utf-8 -*-
# Licensed under a 3-clause BSD style license - see LICENSE.rst

import argparse
import logging
import sys

from .. import util


# This list is ordered in order of average workflow
command_order = [ 'Explode', 'Implode' ]


class Command:
    @classmethod
    def setup_arguments(cls, subparsers):
        raise NotImplementedError()

    @classmethod
    def run(cls, args):
        raise NotImplementedError()


def make_argparser():
    """
    Most of the real work is handled by the subcommands in the
    commands subpackage.
    """
    def help(args):
        parser.print_help()
        return 0

    parser = argparse.ArgumentParser(
        "asdftool",
        description="Commandline utilities for managing ASDF files.")

    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Increase verbosity")

    subparsers = parser.add_subparsers(
        title='subcommands',
        description='valid subcommands')

    help_parser = subparsers.add_parser(
        str("help"), help="Display usage information")
    help_parser.set_defaults(func=help)

    commands = dict((x.__name__, x) for x in util.iter_subclasses(Command))

    for command in command_order:
        commands[str(command)].setup_arguments(subparsers)
        del commands[command]

    for name, command in sorted(commands.items()):
        command.setup_arguments(subparsers)

    return parser, subparsers


def main_from_args(args):
    parser, subparsers = make_argparser()

    args = parser.parse_args(args)

    # Only needed for Python 3, apparently, but can't hurt
    if not hasattr(args, 'func'):
        parser.print_help()
        return 2

    try:
        result = args.func(args)
    except RuntimeError as e:
        logging.error(str(e))
        return 1
    except IOError as e:
        logging.error(str(e))
        return e.errno

    if result is None:
        result = 0

    return result


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    sys.exit(main_from_args(args))
