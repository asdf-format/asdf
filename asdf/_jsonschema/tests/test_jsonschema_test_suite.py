"""
Test runner for the JSON Schema official test suite

Tests comprehensive correctness of each draft's validator.

See https://github.com/json-schema-org/JSON-Schema-Test-Suite for details.
"""

import sys

from asdf._jsonschema.tests._helpers import bug
from asdf._jsonschema.tests._suite import Suite
import asdf._jsonschema


SUITE = Suite()
DRAFT4 = SUITE.version(name="draft4")


def skip(message, **kwargs):
    def skipper(test):
        if all(value == getattr(test, attr) for attr, value in kwargs.items()):
            return message
    return skipper


def missing_format(Validator):
    def missing_format(test):  # pragma: no cover
        schema = test.schema
        if (
            schema is True
            or schema is False
            or "format" not in schema
            or schema["format"] in Validator.FORMAT_CHECKER.checkers
            or test.valid
        ):
            return

        return "Format checker {0!r} not found.".format(schema["format"])
    return missing_format


def complex_email_validation(test):
    if test.subject != "email":
        return

    message = "Complex email validation is (intentionally) unsupported."
    return skip(
        message=message,
        description="an invalid domain",
    )(test) or skip(
        message=message,
        description="an invalid IPv4-address-literal",
    )(test) or skip(
        message=message,
        description="dot after local part is not valid",
    )(test) or skip(
        message=message,
        description="dot before local part is not valid",
    )(test) or skip(
        message=message,
        description="two subsequent dots inside local part are not valid",
    )(test)


is_narrow_build = sys.maxunicode == 2 ** 16 - 1
if is_narrow_build:  # pragma: no cover
    message = "Not running surrogate Unicode case, this Python is narrow."

    def narrow_unicode_build(test):  # pragma: no cover
        return skip(
            message=message,
            description=(
                "one supplementary Unicode code point is not long enough"
            ),
        )(test) or skip(
            message=message,
            description="two supplementary Unicode code points is long enough",
        )(test)
else:
    def narrow_unicode_build(test):  # pragma: no cover
        return


if sys.version_info < (3, 9):  # pragma: no cover
    message = "Rejecting leading zeros is 3.9+"
    allowed_leading_zeros = skip(
        message=message,
        subject="ipv4",
        description="invalid leading zeroes, as they are treated as octals",
    )
else:
    def allowed_leading_zeros(test):  # pragma: no cover
        return


def leap_second(test):
    message = "Leap seconds are unsupported."
    return skip(
        message=message,
        subject="time",
        description="a valid time string with leap second",
    )(test) or skip(
        message=message,
        subject="time",
        description="a valid time string with leap second, Zulu",
    )(test) or skip(
        message=message,
        subject="time",
        description="a valid time string with leap second with offset",
    )(test) or skip(
        message=message,
        subject="time",
        description="valid leap second, positive time-offset",
    )(test) or skip(
        message=message,
        subject="time",
        description="valid leap second, negative time-offset",
    )(test) or skip(
        message=message,
        subject="time",
        description="valid leap second, large positive time-offset",
    )(test) or skip(
        message=message,
        subject="time",
        description="valid leap second, large negative time-offset",
    )(test) or skip(
        message=message,
        subject="time",
        description="valid leap second, zero time-offset",
    )(test) or skip(
        message=message,
        subject="date-time",
        description="a valid date-time with a leap second, UTC",
    )(test) or skip(
        message=message,
        subject="date-time",
        description="a valid date-time with a leap second, with minus offset",
    )(test)


TestDraft4 = DRAFT4.to_unittest_testcase(
    DRAFT4.tests(),
    DRAFT4.format_tests(),
    DRAFT4.optional_tests_of(name="bignum"),
    DRAFT4.optional_tests_of(name="float-overflow"),
    DRAFT4.optional_tests_of(name="non-bmp-regex"),
    DRAFT4.optional_tests_of(name="zeroTerminatedFloats"),
    Validator=asdf._jsonschema.Draft4Validator,
    format_checker=asdf._jsonschema.Draft4Validator.FORMAT_CHECKER,
    skip=lambda test: (
        narrow_unicode_build(test)
        or allowed_leading_zeros(test)
        or leap_second(test)
        or missing_format(asdf._jsonschema.Draft4Validator)(test)
        or complex_email_validation(test)
        or skip(
            message=bug(),
            subject="ref",
            case_description="Recursive references between schemas",
        )(test)
        or skip(
            message=bug(),
            subject="ref",
            case_description=(
                "Location-independent identifier with "
                "base URI change in subschema"
            ),
        )(test)
        or skip(
            message=bug(),
            subject="ref",
            case_description=(
                "$ref prevents a sibling id from changing the base uri"
            ),
        )(test)
        or skip(
            message=bug(),
            subject="id",
            description="match $ref to id",
        )(test)
        or skip(
            message=bug(),
            subject="id",
            description="no match on enum or $ref to id",
        )(test)
        or skip(
            message=bug(),
            subject="refRemote",
            case_description="base URI change - change folder in subschema",
        )(test)
        or skip(
            message=bug(),
            subject="ref",
            case_description=(
                "id must be resolved against nearest parent, "
                "not just immediate parent"
            ),
        )(test)
    ),
)
