"""
Commands for displaying summaries of ASDF trees
"""

from .main import Command
from .. import _convenience as convenience


__all__ = ["info"]


class Info(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            "info", help="Print a rendering of an ASDF tree.",
            description="Print a rendering of an ASDF tree."
        )

        parser.add_argument("filename", help="ASDF file to render")
        parser.add_argument(
            "--max-rows",
            type=int,
            help="maximum number of lines"
        )
        parser.add_argument(
            "--max-cols",
            type=int,
            help="maximum length of line")

        parser.add_argument("--show-values", dest="show_values", action="store_true")
        parser.add_argument("--no-show-values", dest="show_values", action="store_false")
        parser.set_defaults(show_values=True)

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        info(args.filename, args.max_rows, args.max_cols, args.show_values)


def info(filename, max_rows, max_cols, show_values):
    convenience.info(filename, max_rows=max_rows, max_cols=max_cols, show_values=show_values)
