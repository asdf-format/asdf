from __future__ import annotations

from contextlib import suppress
from uuid import UUID
import datetime
import ipaddress
import re
import typing
import warnings

from asdf._jsonschema.exceptions import FormatError

_FormatCheckCallable = typing.Callable[[object], bool]
_F = typing.TypeVar("_F", bound=_FormatCheckCallable)
_RaisesType = typing.Union[
    typing.Type[Exception], typing.Tuple[typing.Type[Exception], ...],
]


class FormatChecker:
    """
    A ``format`` property checker.

    JSON Schema does not mandate that the ``format`` property actually do any
    validation. If validation is desired however, instances of this class can
    be hooked into validators to enable format validation.

    `FormatChecker` objects always return ``True`` when asked about
    formats that they do not know how to validate.

    To add a check for a custom format use the `FormatChecker.checks`
    decorator.

    Arguments:

        formats:

            The known formats to validate. This argument can be used to
            limit which formats will be used during validation.
    """

    checkers: dict[
        str,
        tuple[_FormatCheckCallable, _RaisesType],
    ] = {}

    def __init__(self, formats: typing.Iterable[str] | None = None):
        if formats is None:
            formats = self.checkers.keys()
        self.checkers = {k: self.checkers[k] for k in formats}

    def __repr__(self):
        return "<FormatChecker checkers={}>".format(sorted(self.checkers))

    def checks(
        self, format: str, raises: _RaisesType = (),
    ) -> typing.Callable[[_F], _F]:
        """
        Register a decorated function as validating a new format.

        Arguments:

            format:

                The format that the decorated function will check.

            raises:

                The exception(s) raised by the decorated function when an
                invalid instance is found.

                The exception object will be accessible as the
                `asdf._jsonschema.exceptions.ValidationError.cause` attribute of the
                resulting validation error.
        """

        def _checks(func: _F) -> _F:
            self.checkers[format] = (func, raises)
            return func

        return _checks

    @classmethod
    def cls_checks(
        cls, format: str, raises: _RaisesType = (),
    ) -> typing.Callable[[_F], _F]:
        warnings.warn(
            (
                "FormatChecker.cls_checks is deprecated. Call "
                "FormatChecker.checks on a specific FormatChecker instance "
                "instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        return cls._cls_checks(format=format, raises=raises)

    @classmethod
    def _cls_checks(
        cls, format: str, raises: _RaisesType = (),
    ) -> typing.Callable[[_F], _F]:
        def _checks(func: _F) -> _F:
            cls.checkers[format] = (func, raises)
            return func

        return _checks

    def check(self, instance: object, format: str) -> None:
        """
        Check whether the instance conforms to the given format.

        Arguments:

            instance (*any primitive type*, i.e. str, number, bool):

                The instance to check

            format:

                The format that instance should conform to

        Raises:

            FormatError:

                if the instance does not conform to ``format``
        """

        if format not in self.checkers:
            return

        func, raises = self.checkers[format]
        result, cause = None, None
        try:
            result = func(instance)
        except raises as e:
            cause = e
        if not result:
            raise FormatError(f"{instance!r} is not a {format!r}", cause=cause)

    def conforms(self, instance: object, format: str) -> bool:
        """
        Check whether the instance conforms to the given format.

        Arguments:

            instance (*any primitive type*, i.e. str, number, bool):

                The instance to check

            format:

                The format that instance should conform to

        Returns:

            bool: whether it conformed
        """

        try:
            self.check(instance, format)
        except FormatError:
            return False
        else:
            return True


draft4_format_checker = FormatChecker()

_draft_checkers: dict[str, FormatChecker] = dict(
    draft4=draft4_format_checker,
)


def _checks_drafts(
    name=None,
    draft4=None,
    raises=(),
) -> typing.Callable[[_F], _F]:
    draft4 = draft4 or name

    def wrap(func: _F) -> _F:
        if draft4:
            func = _draft_checkers["draft4"].checks(draft4, raises)(func)

        # Oy. This is bad global state, but relied upon for now, until
        # deprecation. See #519 and test_format_checkers_come_with_defaults
        FormatChecker._cls_checks(
            draft4,
            raises,
        )(func)
        return func

    return wrap


@_checks_drafts(name="idn-email")
@_checks_drafts(name="email")
def is_email(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    return "@" in instance


@_checks_drafts(
    draft4="ipv4",
    raises=ipaddress.AddressValueError,
)
def is_ipv4(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    return bool(ipaddress.IPv4Address(instance))


@_checks_drafts(name="ipv6", raises=ipaddress.AddressValueError)
def is_ipv6(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    address = ipaddress.IPv6Address(instance)
    return not getattr(address, "scope_id", "")


with suppress(ImportError):
    from fqdn import FQDN

    @_checks_drafts(
        draft4="hostname",
    )
    def is_host_name(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        return FQDN(instance).is_valid


try:
    import rfc3987
except ImportError:
    with suppress(ImportError):
        from rfc3986_validator import validate_rfc3986

        @_checks_drafts(name="uri")
        def is_uri(instance: object) -> bool:
            if not isinstance(instance, str):
                return True
            return validate_rfc3986(instance, rule="URI")
else:
    @_checks_drafts(name="uri", raises=ValueError)
    def is_uri(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        return rfc3987.parse(instance, rule="URI")


with suppress(ImportError):
    from rfc3339_validator import validate_rfc3339

    @_checks_drafts(name="date-time")
    def is_datetime(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        return validate_rfc3339(instance.upper())


@_checks_drafts(name="regex", raises=re.error)
def is_regex(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    return bool(re.compile(instance))
