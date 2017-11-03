# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


import os.path

import six

from . import constants
from . import util


SCHEMA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'schemas'))


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
        self._mapping = self._validate_mapping(mapping)[::-1]
        self._prefix = prefix

    def _validate_mapping(self, mappings):
        normalized = []
        for mapping in mappings:
            if six.callable(mapping):
                func = mapping
            elif (isinstance(mapping, (list, tuple)) and
                  len(mapping) == 2 and
                  isinstance(mapping[0], six.string_types) and
                  isinstance(mapping[1], six.string_types)):

                def _make_map_func(mapping):
                    def _map_func(uri):
                        if uri.startswith(mapping[0]):
                            format_tokens = {
                                self._prefix: uri,
                                self._prefix + "_prefix": mapping[0],
                                self._prefix + "_suffix": uri[len(mapping[0]):]
                            }

                            return len(mapping[0]), mapping[1].format(**format_tokens)
                        return None
                    return _map_func

                func = _make_map_func(mapping)
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
                candidates.append((six.MAXSIZE, output))
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
         os.path.join(SCHEMA_PATH, 'stsci.edu')) +
         '/{url_suffix}.yaml'),
    ('tag:stsci.edu:asdf/',
     util.filepath_to_url(
         os.path.join(SCHEMA_PATH, 'stsci.edu')) +
         '/asdf/{url_suffix}.yaml')]


default_url_mapping = Resolver(DEFAULT_URL_MAPPING, 'url')
