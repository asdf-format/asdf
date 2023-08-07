"""
An implementation of JSON Schema for Python

The main functionality is provided by the validator classes for each of the
supported JSON Schema versions.

Most commonly, `asdf._jsonschema.validators.validate` is the quickest way to simply
validate a given instance under a schema, and will create a validator
for you.
"""
import warnings

from asdf._jsonschema._format import FormatChecker
from asdf._jsonschema._types import TypeChecker
from asdf._jsonschema.exceptions import (
    ErrorTree,
    FormatError,
    RefResolutionError,
    SchemaError,
    ValidationError,
)
from asdf._jsonschema.protocols import Validator
from asdf._jsonschema.validators import (
    Draft3Validator,
    Draft4Validator,
    Draft6Validator,
    Draft7Validator,
    Draft201909Validator,
    Draft202012Validator,
    RefResolver,
    validate,
)


def __getattr__(name):
    format_checkers = {
        "draft3_format_checker": Draft3Validator,
        "draft4_format_checker": Draft4Validator,
        "draft6_format_checker": Draft6Validator,
        "draft7_format_checker": Draft7Validator,
        "draft201909_format_checker": Draft201909Validator,
        "draft202012_format_checker": Draft202012Validator,
    }
    ValidatorForFormat = format_checkers.get(name)
    if ValidatorForFormat is not None:
        warnings.warn(
            f"Accessing asdf._jsonschema.{name} is deprecated and will be "
            "removed in a future release. Instead, use the FORMAT_CHECKER "
            "attribute on the corresponding Validator.",
            DeprecationWarning,
            stacklevel=2,
        )
        return ValidatorForFormat.FORMAT_CHECKER

    raise AttributeError(f"module {__name__} has no attribute {name}")
