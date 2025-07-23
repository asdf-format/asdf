"""
Commands for displaying summaries of ASDF trees
"""

import asdf

from .main import Command

__all__ = ["info"]


class Info(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            "info",
            help="Print a rendering of an ASDF tree.",
            description="""Show the contents of an ASDF file by rendering tree contents as text.
            For large files max-rows and max-cols can be used to truncate the output to improve
            readability. When a file contains more lines to display than max-rows the
            deepest parts of the tree will be hidden with a message saying how many
            rows are hidden.""",
        )

        parser.add_argument("filename", help="ASDF file to render")
        parser.add_argument(
            "--max-rows", type=int, help="Maximum number of lines to print. If not provided all lines will be shown."
        )
        parser.add_argument(
            "--max-cols", type=int, help="Maximum length of line. If not provided lines will have no length limit."
        )

        parser.add_argument(
            "--show-values",
            dest="show_values",
            action="store_true",
            help="Display primitive values in the rendered tree (by default, enabled).",
        )
        parser.add_argument("--no-show-values", dest="show_values", action="store_false")
        parser.set_defaults(show_values=True)

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        info(args.filename, args.max_rows, args.max_cols, args.show_values)


def info(filename, max_rows, max_cols, show_values):
    with asdf.open(filename) as af:
        af.info(max_rows, max_cols, show_values)
