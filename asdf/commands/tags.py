# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
Implementation of command for displaying available tags in asdf
"""


import sys

from .main import Command
from .. import AsdfFile


__all__ = ['list_tags']


class TagLister(Command): # pragma: no cover
    """This class is the plugin implementation for the asdftool runner."""
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            str("tags"), help="List currently available tags",
            description="""Lists currently available tags.""")

        parser.add_argument(
            '-d', '--display-classes', action='store_true',
            help="""Display associated class names in addition to tags""")

        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        return list_tags(display_classes=args.display_classes)

def _qualified_name(_class):
    return "{}.{}".format(_class.__module__, _class.__name__)

def list_tags(display_classes=False, iostream=sys.stdout):
    """Function to list tags"""
    af = AsdfFile()
    type_by_tag = af._extensions._type_index._type_by_tag
    tags = sorted(type_by_tag.keys())

    for tag in tags:
        string = str(tag)
        if display_classes:
            string += ":  " + _qualified_name(type_by_tag[tag])
        iostream.write(string + '\n')
