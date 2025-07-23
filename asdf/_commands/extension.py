"""
Implementation of command for reporting information about installed extensions.
"""

from asdf._entry_points import get_extensions

from .main import Command

__all__ = ["find_extensions"]


class QueryExtension(Command):  # pragma: no cover
    """This class is the plugin implementation for the asdftool runner."""

    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            "extensions",
            help="Show information about installed extensions",
            description="""Reports information about installed ASDF extensions""",
        )

        display_group = parser.add_mutually_exclusive_group()
        display_group.add_argument(
            "-s",
            "--summary",
            action="store_true",
            help="Display only the installed extensions themselves",
        )
        display_group.add_argument(
            "-t",
            "--tags-only",
            action="store_true",
            help="Display tags from installed extensions, but no other information",
        )

        parser.set_defaults(func=cls.run)
        return parser

    @classmethod
    def run(cls, args):
        return find_extensions(args.summary, args.tags_only)


def _format_extension(ext):
    uri = "(none)" if ext.extension_uri is None else f"'{ext.extension_uri}'"

    return f"Extension URI: {uri} package: {ext.package_name} ({ext.package_version}) class: {ext.class_name}"


def _format_type_name(type_):
    if isinstance(type_, str):
        return type_

    return f"{type_.__module__}.{type_.__name__}"


def _print_extension_details(ext, tags_only):
    tag_uris = [t.tag_uri for t in ext.tags]
    for typ in ext.types:
        if isinstance(typ.name, list):
            for name in typ.name:
                tag_uris.append(typ.make_yaml_tag(name))
        elif typ.name is not None:
            tag_uris.append(typ.make_yaml_tag(typ.name))

    if len(tag_uris) > 0:
        print("tags:")
        for tag_uri in sorted(tag_uris):
            print(f"  - {tag_uri}")

    if not tags_only:
        types = []
        for converter in ext.converters:
            for typ in converter.types:
                types.append(typ)
        for typ in ext.types:
            types.extend(typ.types)

        if len(types) > 0:
            print("types:")
            for typ in sorted(types, key=_format_type_name):
                print(f"  - {_format_type_name(typ)}")


def find_extensions(summary, tags_only):
    for ext in get_extensions():
        print(_format_extension(ext))
        if not summary:
            _print_extension_details(ext, tags_only)
            print()
