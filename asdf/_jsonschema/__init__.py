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
    Draft4Validator,
    RefResolver,
    validate,
)


def __getattr__(name):
    format_checkers = {
        "draft4_format_checker": Draft4Validator,
    }
    ValidatorForFormat = format_checkers.get(name)
    if ValidatorForFormat is not None:
        return ValidatorForFormat.FORMAT_CHECKER

    raise AttributeError(f"module {__name__} has no attribute {name}")
