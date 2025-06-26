"""
Contains commands for dealing with exploded and imploded forms.
"""

import os

import asdf
from asdf import AsdfFile

from .main import Command

__all__ = ["to_yaml"]


class ToYaml(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            "to_yaml",
            help="Convert as ASDF file to pure YAML.",
            description="""Convert all data to inline YAML so the ASDF
            file contains no binary blocks.""",
        )

        parser.add_argument("filename", nargs=1, help="""The ASDF file to convert to YAML.""")
        parser.add_argument(
            "--output",
            "-o",
            type=str,
            nargs="?",
            help="""The name of the output file.  If not provided, it
            will be the name of the input file with a '.yaml' extension.""",
        )
        parser.add_argument(
            "--resolve-references",
            "-r",
            action="store_true",
            help="""Resolve all references and store them directly in
            the output file.""",
        )

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        return to_yaml(args.filename[0], args.output, args.resolve_references)


def to_yaml(input_, output=None, resolve_references=False):
    """
    Implode a given ASDF file, which may reference external data, back
    into a single ASDF file.

    Parameters
    ----------
    input_ : str or file-like object
        The input file.

    output : str of file-like object
        The output file.

    resolve_references : bool, optional
        If `True` resolve all external references before saving.
    """
    if output is None:
        base, _ = os.path.splitext(input_)
        output = base + ".yaml"
    with asdf.open(input_) as ff:
        ff2 = AsdfFile(ff)
        if resolve_references:
            ff2.resolve_references()
        ff2.write_to(output, all_array_storage="inline")
