"""
Implementation of command for displaying available tags in asdf
"""

import sys

from asdf import AsdfFile

from .main import Command

__all__ = ["list_tags"]


class TagLister(Command):  # pragma: no cover
    """This class is the plugin implementation for the asdftool runner."""

    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            "tags",
            help="List currently available tags",
            description="""Lists currently available tags.""",
        )

        parser.add_argument(
            "-d",
            "--display-classes",
            action="store_true",
            help="""Display associated class names in addition to tags""",
        )

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        return list_tags(display_classes=args.display_classes)


def _format_type(typ):
    if isinstance(typ, str):
        return typ

    return f"{typ.__module__}.{typ.__name__}"


def list_tags(display_classes=False, iostream=sys.stdout):
    """Function to list tags"""
    af = AsdfFile()

    tag_pairs = []
    for tag in af.extension_manager._converters_by_tag:
        tag_pairs.append((tag, af.extension_manager.get_converter_for_tag(tag).types))

    for tag, types in sorted(tag_pairs, key=lambda pair: pair[0]):
        string = str(tag)
        if display_classes:
            string += ":  " + ", ".join(_format_type(t) for t in types)
        iostream.write(string + "\n")
