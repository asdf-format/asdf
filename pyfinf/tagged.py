# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
This file manages a transient representation of the tree made up of
simple Python data types (lists, dicts, scalars) wrapped inside of
`Tagged` subclasses, which add a ``tag`` attribute to hold the
associated YAML tag.

Below "basic data types" refers to the basic built-in data types
defined in the core YAML specification.  "Custom data types" are
specialized tags that are added by FINF or third-parties that are not
in the YAML specification.

When YAML is loaded from disk, we want to first validate it using JSON
schema, which only understands basic Python data types, not the
``Nodes`` that ``pyyaml`` uses as its intermediate representation.
However, basic Python data types do not preserve the tag information
from the YAML file that we need later to convert elements to custom
data types.  Therefore, the approach here is to wrap those basic types
inside of `Tagged` objects long enough to run through the jsonschema
validator, and then convert to custom data types and throwing away the
tag annotations in the process.

Upon writing, the custom data types are first converted to basic
Python data types wrapped in `Tagged` objects.  The tags assigned to
the ``Tagged`` objects are then used to write tags to the YAML file.

All of this is an implementation detail of the our custom YAML loader
and dumper (``yamlutil.FinfLoader`` and ``yamlutil.FinfDumper``) and
is not intended to be exposed to the end user.
"""

from __future__ import absolute_import, division, unicode_literals, print_function


from astropy.extern import six
from .compat import UserDict, UserList, UserString


__all__ = ['tag_object', 'get_tag', 'walk_and_modify_with_tags']


class Tagged(object):
    """
    Base class of classes that wrap a given object and store a tag
    with it.
    """
    pass


class TaggedDict(Tagged, UserDict, dict):
    """
    A Python dict with a tag attached.
    """
    def __init__(self, data=None, tag=None):
        if data is None:
            data = {}
        self.data = data
        self.tag = tag


class TaggedList(Tagged, UserList, list):
    """
    A Python list with a tag attached.
    """
    def __init__(self, data=None, tag=None):
        if data is None:
            data = []
        self.data = data
        self.tag = tag


class TaggedString(Tagged, UserString, six.text_type):
    """
    A Python list with a tag attached.
    """
    pass


def tag_object(tag, instance):
    """
    Tag an object by wrapping it in a ``Tagged`` instance.
    """
    if tag is None:
        return instance

    if isinstance(instance, Tagged):
        instance.tag = tag
        return instance
    elif isinstance(instance, dict):
        return TaggedDict(instance, tag)
    elif isinstance(instance, list):
        return TaggedList(instance, tag)
    elif isinstance(instance, six.string_types):
        instance = TaggedString(instance)
        instance.tag = tag
        return instance
    else:
        raise TypeError(
            "Don't know how to tag a {0}".format(type(instance)))


def get_tag(instance):
    """
    Get the tag associated with the instance, if there is one.
    """
    if isinstance(instance, Tagged):
        return instance.tag
    return None


def walk_and_modify_with_tags(top, callback):
    """
    Modify a tree by walking it with a callback function.  Unlike
    `tree.walk_and_modify`, this version knows how to preserve tag
    information.

    Parameters
    ----------
    top : object
        The root of the tree.  May be a dict, list or other Python object.

    callback : callable
        A function to call at each node in the tree.  It takes and
        instance and may return a different instance in order to
        modify the tree.

        The callback is called on an instance after all of its
        children have been visited (depth-first order).

    Returns
    -------
    tree : object
        The modified tree.
    """
    def recurse(tree):
        if isinstance(tree, dict):
            result = tree.__class__()
            for key, val in six.iteritems(tree):
                result[key] = recurse(val)
            if isinstance(tree, Tagged):
                result = tag_object(tree.tag, result)
        elif isinstance(tree, (list, tuple)):
            result = tree.__class__([recurse(val) for val in tree])
            if isinstance(tree, Tagged):
                result = tag_object(tree.tag, result)
        else:
            result = tree

        result = callback(result)

        return result

    return recurse(top)
