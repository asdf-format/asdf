# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
Contains commands for dealing with exploded and imploded forms.
"""


import os

import asdf
from .main import Command
from .. import AsdfFile


__all__ = ['implode', 'explode']


class Implode(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            str("implode"), help="Implode a ASDF file.",
            description="""Combine a ASDF file, where the data may be
            stored in multiple ASDF files, into a single ASDF
            file.""")

        parser.add_argument(
            'filename', nargs=1,
            help="""The ASDF file to implode.""")
        parser.add_argument(
            "--output", "-o", type=str, nargs="?",
            help="""The name of the output file.  If not provided, it
            will be the name of the input file with "_all"
            appended.""")
        parser.add_argument(
            "--resolve-references", "-r", action="store_true",
            help="""Resolve all references and store them directly in
            the output file.""")

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        return implode(args.filename[0], args.output, args.resolve_references)


def implode(input, output=None, resolve_references=False):
    """
    Implode a given ASDF file, which may reference external data, back
    into a single ASDF file.

    Parameters
    ----------
    input : str or file-like object
        The input file.

    output : str of file-like object
        The output file.

    resolve_references : bool, optional
        If `True` resolve all external references before saving.
    """
    if output is None:
        base, ext = os.path.splitext(input)
        output = base + '_all' + '.asdf'
    with asdf.open(input) as ff:
        ff2 = AsdfFile(ff)
        if resolve_references:
            ff2.resolve_references()
        ff2.write_to(output, all_array_storage='internal')


class Explode(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            str("explode"), help="Explode a ASDF file.",
            description="""From a single ASDF file, create a set of
            ASDF files where each data block is stored in a separate
            file.""")

        parser.add_argument(
            'filename', nargs=1,
            help="""The ASDF file to explode.""")
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
    Explode a given ASDF file so each data block is in a separate
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
        output = base + '_exploded' + '.asdf'
    with asdf.open(input) as ff:
        ff.write_to(output, all_array_storage='external')
