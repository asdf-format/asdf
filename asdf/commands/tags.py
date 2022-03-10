"""
Implementation of command for displaying available tags in asdf
"""


import sys

from asdf import get_config

from .main import Command

__all__ = ["list_tags"]


class TagLister(Command):  # pragma: no cover
    """This class is the plugin implementation for the asdftool runner."""

    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            str("tags"), help="List currently available tags", description="""Lists currently available tags."""
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
    else:
        return "{}.{}".format(typ.__module__, typ.__name__)


def list_tags(display_classes=False, iostream=sys.stdout):
    """Function to list tags"""
    extension_manager = get_config().get_extension_manager(get_config().default_version)
    type_index = get_config().extension_list.type_index

    tag_pairs = []
    for tag in extension_manager._converters_by_tag:
        tag_pairs.append((tag, extension_manager.get_converter_for_tag(tag).types))
    for tag in type_index._type_by_tag:
        tag_pairs.append((tag, [type_index._type_by_tag[tag]]))

    for tag, types in sorted(tag_pairs, key=lambda pair: pair[0]):
        string = str(tag)
        if display_classes:
            string += ":  " + ", ".join(_format_type(t) for t in types)
        iostream.write(string + "\n")
