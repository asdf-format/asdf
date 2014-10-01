# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


import os.path

from astropy.extern import six

from . import constants


SCHEMA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'schemas'))


class Resolver(object):
    """
    A class that can be used to map strings with a particular prefix
    to another.
    """
    builtin = []

    def __init__(self, mapping=[]):
        """
        Parameters
        ----------
        mapping : list of tuple or callable, optional
            A list of mappings to try, in order.  The builtin mappings
            for ASDF will prepended to the provided mappings.
            For each entry:

            - If a callable, must take a string and return a remapped
              string.  Should return `None` if the mapping does not
              apply to the input.

            - If a tuple, the first item is a string prefix to match.
              The second item specifies how to create the new result
              in Python string formatting syntax.  `{}` will be
              replaced with the matched string without the prefix.
        """
        self._mapping = self._validate_mapping(
            self.builtin + mapping)

    def _validate_mapping(self, mappings):
        normalized = []
        for mapping in mappings:
            if six.callable(mapping):
                func = mapping
                pass
            elif (isinstance(mapping, (list, tuple)) and
                  len(mapping) == 2 and
                  isinstance(mapping[0], six.string_types) and
                  isinstance(mapping[1], six.string_types)):

                def _map_func(uri):
                    if uri.startswith(mapping[0]):
                        rest = uri[len(mapping[0]):]
                        return mapping[1].format(rest)
                    return None

                func = _map_func
            else:
                raise ValueError("Invalid mapping '{0}'".format(mapping))

            normalized.append(func)

        return tuple(normalized)

    def __call__(self, input):
        for mapper in self._mapping:
            output = mapper(input)
            if output is not None:
                return output
        return input

    def __hash__(self):
        return hash(self._mapping)


class TagToSchemaResolver(Resolver):
    """
    The default mapping from YAML tags to schema URLs.
    """
    builtin = [
        ('tag:stsci.edu:asdf', 'http://stsci.edu/schemas/asdf{0}')
    ]

# The singleton
TAG_TO_SCHEMA_RESOLVER = TagToSchemaResolver()

class UrlMapping(Resolver):
    """
    The default mapping from remote schema URLs to the schemas that
    ship with pyasdf.
    """
    builtin = [
        (constants.STSCI_SCHEMA_URI_BASE,
         'file://' + SCHEMA_PATH + '/stsci.edu/{0}.yaml')]

# The singleton
URL_MAPPING = UrlMapping()
