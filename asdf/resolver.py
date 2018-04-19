# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import sys
import os.path

from . import constants
from . import util


def find_schema_path():
    dirname = os.path.dirname(__file__)

    # This means we are working within a development build
    if os.path.exists(os.path.join(dirname, '..', 'asdf-standard')):
        return os.path.join(dirname, '..', 'asdf-standard', 'schemas')

    # Otherwise, we return the installed location
    return os.path.join(dirname, 'schemas')


class Resolver(object):
    """
    A class that can be used to map strings with a particular prefix
    to another.
    """
    def __init__(self, mapping=[], prefix=''):
        """
        Parameters
        ----------
        mapping : list of tuple or callable, optional
            A list of mappings to try, in order.
            For each entry:

            - If a callable, must take a string and return a remapped
              string.  Should return `None` if the mapping does not
              apply to the input.

            - If a tuple, the first item is a string prefix to match.
              The second item specifies how to create the new result
              in Python string formatting syntax.  The following
              formatting tokens are available, where ``X`` relates to
              the ``prefix`` argument:

              - ``{X}``: The entire string passed in.
              - ``{X_prefix}``: The prefix of the string that was
                matched.
              - ``{X_suffix}``: The part of the string following the
                prefix.

        prefix : str, optional
            The prefix to use for the Python formatting token names.
        """
        self._mapping = tuple()
        if mapping:
            self.add_mapping(mapping, prefix)

    def add_mapping(self, mapping, prefix=''):
        self._mapping = self._mapping + self._validate_mapping(mapping, prefix)

    def _make_map_func(self, mapping, prefix):
        def _map_func(uri):
            if uri.startswith(mapping[0]):
                format_tokens = {
                    prefix: uri,
                    prefix + "_prefix": mapping[0],
                    prefix + "_suffix": uri[len(mapping[0]):]
                }

                return len(mapping[0]), mapping[1].format(**format_tokens)
            return None
        return _map_func

    def _validate_mapping(self, mappings, prefix):
        normalized = []
        for mapping in mappings:
            if callable(mapping):
                func = mapping
            elif (isinstance(mapping, (list, tuple)) and
                  len(mapping) == 2 and
                  isinstance(mapping[0], str) and
                  isinstance(mapping[1], str)):

                func = self._make_map_func(mapping, prefix)
            else:
                raise ValueError("Invalid mapping '{0}'".format(mapping))

            normalized.append(func)

        return tuple(normalized)

    def __call__(self, input):
        candidates = []
        for mapper in self._mapping:
            output = mapper(input)
            if isinstance(output, tuple):
                candidates.append(output)
            elif output is not None:
                candidates.append((sys.maxsize, output))
        if len(candidates):
            candidates.sort()
            return candidates[-1][1]
        else:
            return input

    def __hash__(self):
        return hash(self._mapping)


DEFAULT_URL_MAPPING = [
    (constants.STSCI_SCHEMA_URI_BASE,
     util.filepath_to_url(
         os.path.join(find_schema_path(), 'stsci.edu')) +
         '/{url_suffix}.yaml')]
DEFAULT_TAG_TO_URL_MAPPING = [
    (constants.STSCI_SCHEMA_TAG_BASE,
     'http://stsci.edu/schemas/asdf{tag_suffix}')
]


default_url_mapping = Resolver(DEFAULT_URL_MAPPING, 'url')
default_tag_to_url_mapping = Resolver(DEFAULT_TAG_TO_URL_MAPPING, 'tag')

def default_resolver(uri):
    return default_url_mapping(default_tag_to_url_mapping(uri))
