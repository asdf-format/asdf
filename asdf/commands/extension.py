# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
Implementation of command for reporting information about installed extensions.
"""

from pkg_resources import iter_entry_points

from .main import Command


class QueryExtension(Command): # pragma: no cover
    """This class is the plugin implementation for the asdftool runner."""
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            "extensions", help="Show information about installed extensions",
            description="""Reports information about installed ASDF extensions""")

        parser.set_defaults(func=cls.run)
        return parser

    @classmethod
    def run(cls, args):
        return find_extensions()


def _format_entry_point(ep):
    extension_class = "{}.{}".format(ep.module_name, ep.attrs[0])
    return "Extension Name: '{}' (from {}) Class: {}".format(
        ep.name, ep.dist, extension_class)


def _format_type_name(typ):
    return "{}.{}".format(typ.__module__, typ.__name__)


def _tag_comparator(a, b):
    return _format_type_name(a) < _format_type_name(b)


def find_extensions():

    for ep in iter_entry_points(group='asdf_extensions'):
        print(_format_entry_point(ep))
        ext = ep.load()()
        for typ in sorted(ext.types, key=lambda x: _format_type_name(x)):
            if typ.name is not None:
                print("-  " + _format_type_name(typ))
                print("      implements: {}".format(typ.make_yaml_tag(typ.name)))
                if typ.types:
                    print("      serializes:")
                    for name in typ.types:
                        print("      - {}".format(_format_type_name(name)))
        print()
