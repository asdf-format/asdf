# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import sys
import os.path
import warnings

from . import constants
from . import util
from .exceptions import AsdfDeprecationWarning


def find_schema_path():
    dirname = os.path.dirname(__file__)

    # This means we are working within a development build
    if os.path.exists(os.path.join(dirname, '..', 'asdf-standard')):
        return os.path.join(dirname, '..', 'asdf-standard', 'schemas')

    # Otherwise, we return the installed location
    return os.path.join(dirname, 'schemas')


class Resolver:
    """
    A class that can be used to map strings with a particular prefix
    to another.
    """
    def __init__(self, mappings, prefix):
        """
        Parameters
        ----------
        mappings : list of tuple or callable
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

        prefix : str
            The prefix to use for the Python formatting token names.
        """
        self._mappings = self._validate_mappings(mappings)
        self._prefix = prefix


    def add_mapping(self, mappings, prefix=''):
        # Deprecating this because Resolver is used as part of a dictionary key
        # and so shouldn't be mutable.
        assert prefix == self._prefix

        warnings.warn("The 'add_mapping' method is deprecated.", AsdfDeprecationWarning)
        self._mappings = self._mappings + self._validate_mappings(mappings)


    def _perform_mapping(self, mapping, input):
        if callable(mapping):
            output = mapping(input)
            if output is not None:
                return (sys.maxsize, mapping(input))
            else:
                return None
        else:
            if input.startswith(mapping[0]):
                format_tokens = {
                    self._prefix: input,
                    self._prefix + "_prefix": mapping[0],
                    self._prefix + "_suffix": input[len(mapping[0]):]
                }

                return len(mapping[0]), mapping[1].format(**format_tokens)
            else:
                return None

    def _validate_mappings(self, mappings):
        normalized = []
        for mapping in mappings:
            if callable(mapping):
                normalized.append(mapping)
            elif (isinstance(mapping, (list, tuple)) and
                  len(mapping) == 2 and
                  isinstance(mapping[0], str) and
                  isinstance(mapping[1], str)):
                normalized.append(tuple(mapping))
            else:
                raise ValueError("Invalid mapping '{0}'".format(mapping))

        return tuple(normalized)


    def __call__(self, input):
        candidates = [(0, input)]
        for mapping in self._mappings:
            output = self._perform_mapping(mapping, input)
            if output is not None:
                candidates.append(output)

        candidates.sort()
        return candidates[-1][1]

    def __hash__(self):
        return hash(self._mappings)

    def __eq__(self, other):
        if not isinstance(other, Resolver):
            return NotImplemented

        return self._mappings == other._mappings


class ResolverChain:
    """
    A chain of Resolvers, each of which is called with the previous Resolver's
    output to produce the final transformed string.
    """
    def __init__(self, *resolvers):
        """
        Parameters
        ----------
        *resolvers : list of Resolver
            Resolvers to include in the chain.
        """
        self._resolvers = tuple(resolvers)

    def __call__(self, input):
        for resolver in self._resolvers:
            input = resolver(input)
        return input

    def __hash__(self):
        return hash(self._resolvers)

    def __eq__(self, other):
        if not isinstance(other, ResolverChain):
            return NotImplemented

        return self._resolvers == other._resolvers


DEFAULT_URL_MAPPING = [
    (constants.STSCI_SCHEMA_URI_BASE,
     util.filepath_to_url(
         os.path.join(find_schema_path(), 'stsci.edu')) +
         '/{url_suffix}.yaml')]
DEFAULT_TAG_TO_URL_MAPPING = [
    (constants.STSCI_SCHEMA_TAG_BASE,
     'http://stsci.edu/schemas/asdf{tag_suffix}')
]

def default_url_mapping(uri):
    warnings.warn("'default_url_mapping' is deprecated.", AsdfDeprecationWarning)
    return default_url_mapping._resolver(uri)
default_url_mapping._resolver = Resolver(DEFAULT_URL_MAPPING, 'url')

def default_tag_to_url_mapping(uri):
    warnings.warn("'default_tag_to_url_mapping' is deprecated.", AsdfDeprecationWarning)
    return default_tag_to_url_mapping._resolver(uri)
default_tag_to_url_mapping._resolver = Resolver(DEFAULT_TAG_TO_URL_MAPPING, 'tag')

def default_resolver(uri):
    warnings.warn(
        "The 'default_resolver(...)' function is deprecated. Use "
        "'asdf.extension.get_default_resolver()(...)' instead.",
        AsdfDeprecationWarning)
    return default_resolver._resolver(uri)
default_resolver._resolver = ResolverChain(default_tag_to_url_mapping._resolver, default_url_mapping._resolver)
