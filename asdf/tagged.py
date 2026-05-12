"""
This file manages a transient representation of the tree made up of
simple Python data types (lists, dicts, scalars) wrapped inside of
`Tagged` subclasses, which add a ``tag`` attribute to hold the
associated YAML tag.

Below "basic data types" refers to the basic built-in data types
defined in the core YAML specification.  "Custom data types" are
specialized tags that are added by ASDF or third-parties that are not
in the YAML specification.

When YAML is loaded from disk, we want to first validate it using JSON
schema, which only understands basic Python data types, not the
``Nodes`` that ``pyyaml`` uses as its intermediate representation.
However, basic Python data types do not preserve the tag information
from the YAML file that we need later to convert elements to custom
data types.  Therefore, the approach here is to wrap those basic types
inside of `Tagged` objects long enough to run through the asdf._jsonschema
validator, and then convert to custom data types and throwing away the
tag annotations in the process.

Upon writing, the custom data types are first converted to basic
Python data types wrapped in `Tagged` objects.  The tags assigned to
the ``Tagged`` objects are then used to write tags to the YAML file.

All of this is an implementation detail of the our custom YAML loader
and dumper (``yamlutil.AsdfLoader`` and ``yamlutil.AsdfDumper``) and
is not intended to be exposed to the end user.
"""

from __future__ import annotations

from collections import UserDict, UserList, UserString
from copy import copy, deepcopy
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

if TYPE_CHECKING:
    from asdf import AsdfFile

__all__ = ["Tagged", "TaggedDict", "TaggedList", "TaggedString", "get_tag", "tag_object"]

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class Tagged(Generic[T]):
    """
    Base class of classes that wrap a given object and store a tag
    with it.
    """

    _base_type: type[T]
    _tag: str | None = None

    @property
    def base(self):
        """Convert to base type"""

        return self._base_type(self)  # pyrefly: ignore [bad-argument-count]


class TaggedDict(Generic[K, V], Tagged[dict[K, V]], UserDict[K, V], dict[K, V]):
    """
    A Python dict with a tag attached.
    """

    _base_type = dict

    flow_style = None
    property_order = None

    def __init__(self, data=None, tag=None):
        if data is None:
            data = {}
        self.data = data
        self._tag = tag

    def __eq__(self, other):
        return isinstance(other, TaggedDict) and self.data == other.data and self._tag == other._tag

    def __deepcopy__(self, memo):
        data_copy = deepcopy(self.data, memo)
        return TaggedDict(data_copy, self._tag)

    def __copy__(self):
        data_copy = copy(self.data)
        return TaggedDict(data_copy, self._tag)


class TaggedList(Generic[T], Tagged[list[T]], UserList[T], list[T]):
    """
    A Python list with a tag attached.
    """

    _base_type = list

    flow_style = None

    def __init__(self, data=None, tag=None):
        if data is None:
            data = []
        self.data = data
        self._tag = tag

    def __eq__(self, other):
        return isinstance(other, TaggedList) and self.data == other.data and self._tag == other._tag

    def __deepcopy__(self, memo):
        data_copy = deepcopy(self.data, memo)
        return TaggedList(data_copy, self._tag)

    def __copy__(self):
        data_copy = copy(self.data)
        return TaggedList(data_copy, self._tag)


class TaggedString(Tagged[str], UserString, str):
    """
    A Python string with a tag attached.
    """

    _base_type = str

    style = None

    def __eq__(self, string):
        return isinstance(string, TaggedString) and str.__eq__(self, string) and self._tag == string._tag


_Tagged = TypeVar("_Tagged", bound=Tagged)


# Define specific overloads mapping types to their tagged versions
@overload
def tag_object(tag: str, instance: _Tagged, ctx: AsdfFile | None = ...) -> _Tagged: ...
@overload
def tag_object(tag: str, instance: dict[Any, Any], ctx: AsdfFile | None = ...) -> TaggedDict: ...
@overload
def tag_object(tag: str, instance: list[Any], ctx: AsdfFile | None = ...) -> TaggedList: ...
@overload
def tag_object(tag: str, instance: str, ctx: AsdfFile | None = ...) -> TaggedString: ...
@overload
def tag_object(tag: str, instance: Any, ctx: AsdfFile | None = ...) -> Tagged: ...


def tag_object(tag, instance, ctx=None):
    """
    Tag an object by wrapping it in a ``Tagged`` instance.
    """
    if isinstance(instance, Tagged):
        instance._tag = tag
    elif isinstance(instance, dict):
        instance = TaggedDict(instance, tag)
    elif isinstance(instance, list):
        instance = TaggedList(instance, tag)
    elif isinstance(instance, str):
        instance = TaggedString(instance)
        instance._tag = tag
    else:
        from . import AsdfFile, yamlutil

        if ctx is None:
            ctx = AsdfFile()
        try:
            instance = yamlutil.custom_tree_to_tagged_tree(instance, ctx)
        except TypeError as err:
            msg = f"Don't know how to tag a {type(instance)}"
            raise TypeError(msg) from err
        instance._tag = tag
    return instance


@overload
def get_tag(instance: Tagged) -> str: ...
@overload
def get_tag(instance: Any) -> None: ...


def get_tag(instance):
    """
    Get the tag associated with the instance, if there is one.
    """
    if not isinstance(instance, Tagged):
        return None
    return getattr(instance, "_tag", None)
