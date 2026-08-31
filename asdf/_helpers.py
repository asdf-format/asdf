from dataclasses import dataclass
from typing import Any, Generic, final

from typing_extensions import TypeVar

from . import versioning
from ._version import version as asdf_package_version

_T = TypeVar("_T")


def validate_version(version):
    # Account for the possibility of AsdfVersion
    version = str(version)
    if version not in versioning.supported_versions:
        msg = "ASDF Standard version {} is not supported by asdf=={}.  Available ASDF Standard versions: {}".format(
            version,
            asdf_package_version,
            ", ".join(str(v) for v in versioning.supported_versions),
        )
        raise ValueError(msg)
    return version


@final
class is_set(Generic[_T]):
    """Can be passed an object with `tracked_property` attributes to check if a property has been set.

    See `tracked_property` for usage examples.
    """

    __slots__ = ("_inner",)

    def __init__(self, inner: _T):
        self._inner = inner

    def __dir__(self):
        return dir(self._inner)

    def __getattr__(self, name: str) -> bool:
        cache = self._inner.__dict__

        try:
            attr = cache[name]
        except KeyError:
            # This will raise an AttributeError if the attribute doesn't exist on the inner type
            prop = getattr(self._inner.__class__, name)
            if isinstance(prop, tracked_property):
                attr = _get_attr(self._inner, name)
            else:
                attr = None

        if not isinstance(attr, _IsSetAttr):
            msg = f"{name} is not a tracked_property"
            raise TypeError(msg)

        return attr.is_set


class tracked_property(property):
    """Extension to `property` that allows tracking whether a property's value has been
    manually set after being initialized (even if set to its original value).

    The decorated attribute behaves like a normal property when accessed from its parent object.
    Passing the parent object to `is_set` returns a wrapper that reports whether each tracked
    attribute has been manually set.

    Examples
    --------
        >>> class Config:
        ...     def __init__(self):
        ...         self._value = 1
        ...
        ...     @tracked_property
        ...     def value(self):
        ...         return self._value
        ...
        ...     @value.setter
        ...     def value(self, value):
        ...         self._value = value
        >>> cfg = Config()
        >>> is_set(cfg).value
        False
        >>> cfg.value = 2
        >>> is_set(cfg).value
        True
    """

    def __set_name__(self, owner: type[Any], name: str) -> None:
        self.__name__ = name

    def __set__(self, instance: object, value: Any) -> None:
        _get_attr(instance, self.__name__).is_set = True
        return super().__set__(instance, value)


@dataclass(slots=True)
class _IsSetAttr:
    """Class that stores attribute metadata for `is_set`/`tracked_property`."""

    is_set: bool = False


def _get_attr(obj: object, attr: str) -> _IsSetAttr:
    """Helper that gets or creates the `_IsSetAttr` corresponding to an attribute."""
    # This function uses the same semantics as functools.cached_property
    # where `_IsSetAttr` is stored in the instance __dict__ under the corresponding property name.
    # This works because the property is only part of the class-level __dict__
    # so the key should be empty in the instance __dict__.
    try:
        cache = obj.__dict__
    except AttributeError:
        msg = f"No '__dict__' attribute on {type(obj).__name__} instance to store tracked_property metadata"
        raise TypeError(msg) from None
    if attr not in cache:
        cache[attr] = _IsSetAttr()

    return cache[attr]
