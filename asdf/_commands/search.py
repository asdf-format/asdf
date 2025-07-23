"""
Commands for searching ASDF trees
"""

import json

import asdf

from .main import Command

__all__ = ["search"]


class Search(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            "search",
            help="Search an ASDF file.",
            description="Search the contents of an ASDF file and render the search result as text.",
        )

        parser.add_argument("filename", help="ASDF file to search")
        parser.add_argument(
            "--key",
            type=str,
            help="If provided, search the ASDF tree for keys that match the provided regular expression.",
        )
        parser.add_argument(
            "--type",
            type=str,
            help=(
                "If provided, search the ASDF tree for nodes of the provided type. "
                "Must be an importable path or member of builtins. "
                "For arrays either numpy.ndarray or asdf.tags.core.ndarray.NDArrayType can be used."
            ),
        )
        parser.add_argument(
            "--value",
            type=str,
            help=(
                "If provided, search the ASDF tree for nodes that match the provided value. "
                "The provided string will be json decoded (and fall back to the raw string if json decoding fails)."
            ),
        )
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
        search(args.filename, args.key, args.type, args.value, args.max_rows, args.max_cols, args.show_values)


def search(filename, key, type_, value, max_rows, max_cols, show_values):
    query = {}
    if key is not None:
        query["key"] = key
    if type_ is not None:
        if type_ == "numpy.ndarray":
            type_ = "asdf.tags.core.ndarray.NDArrayType"
        if "." not in type_:
            type_ = f"builtins.{type_}"
        module, class_name = type_.rsplit(".", maxsplit=1)
        query["type_"] = getattr(__import__(module, fromlist=[class_name]), class_name)
    if value is not None:
        try:
            value = json.loads(value)
        except json.decoder.JSONDecodeError:
            pass
        query["value"] = value
    with asdf.open(filename) as af:
        result = af.search(**query)
        print(result.format(max_rows, max_cols, show_values))
