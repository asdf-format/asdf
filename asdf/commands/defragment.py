# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
Defragment command.
"""

import asdf
from .main import Command
from .. import AsdfFile


__all__ = ['defragment']


class Defragment(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            str("defragment"), help="Defragment an ASDF file..",
            description="""Removes any unused blocks and unused space.""")

        parser.add_argument(
            'filename', nargs=1,
            help="""The ASDF file to collect.""")
        parser.add_argument(
            "--output", "-o", type=str, nargs="?",
            help="""The name of the output file.""")
        parser.add_argument(
            "--resolve-references", "-r", action="store_true",
            help="""Resolve all references and store them directly in
            the output file.""")
        parser.add_argument(
            "--compress", "-c", type=str, nargs="?",
            choices=['zlib', 'bzp2', 'lz4'],
            help="""Compress blocks using one of "zlib", "bzp2" or "lz4".""")

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        return defragment(args.filename[0], args.output,
                          args.resolve_references, args.compress)


def defragment(input, output=None, resolve_references=False, compress=None):
    """
    Defragment a given ASDF file.

    Parameters
    ----------
    input : str or file-like object
        The input file.

    output : str of file-like object
        The output file.

    resolve_references : bool, optional
        If `True` resolve all external references before saving.

    compress : str, optional
        Compression to use.
    """
    with asdf.open(input) as ff:
        ff2 = AsdfFile(ff)
        if resolve_references:
            ff2.resolve_references()
        ff2.write_to(
            output,
            all_array_storage='internal',
            all_array_compression=compress)
