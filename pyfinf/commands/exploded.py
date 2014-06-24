# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
Contains commands for dealing with exploded and imploded forms.
"""

from __future__ import absolute_import, division, unicode_literals, print_function

import os

from .main import Command
from .. import FinfFile


__all__ = ['implode', 'explode']


class Implode(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            str("implode"), help="Implode a FINF file.",
            description="""Combine a FINF file, where the data may be
            stored in multiple FINF files, into a single FINF
            file.""")

        parser.add_argument(
            'filename', nargs=1,
            help="""The FINF file to implode.""")
        parser.add_argument(
            "--output", "-o", type=str, nargs="?",
            help="""The name of the output file.  If not provided, it
            will be the name of the input file with "_all"
            appended.""")

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        return implode(args.filename[0], args.output)


def implode(input, output=None):
    """
    Implode a given FINF file, which may reference external data, back
    into a single FINF file.

    Parameters
    ----------
    input : str or file-like object
        The input file.

    output : str of file-like object
        The output file.
    """
    if output is None:
        base, ext = os.path.splitext(input)
        output = base + '_all' + '.finf'
    with FinfFile.read(input) as ff:
        with FinfFile(ff).write_to(output, exploded=False):
            pass


class Explode(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            str("explode"), help="Explode a FINF file.",
            description="""From a single FINF file, create a set of
            FINF files where each data block is stored in a separate
            file.""")

        parser.add_argument(
            'filename', nargs=1,
            help="""The FINF file to explode.""")
        parser.add_argument(
            "--output", "-o", type=str, nargs="?",
            help="""The name of the output file.  If not provided, it
            will be the name of the input file with "_exploded"
            appended.""")

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        return explode(args.filename[0], args.output)


def explode(input, output=None):
    """
    Explode a given FINF file so each data block is in a separate
    file.

    Parameters
    ----------
    input : str or file-like object
        The input file.

    output : str of file-like object
        The output file.
    """
    if output is None:
        base, ext = os.path.splitext(input)
        output = base + '_exploded' + '.finf'
    with FinfFile.read(input) as ff:
        with FinfFile(ff).write_to(output, exploded=True):
            pass
