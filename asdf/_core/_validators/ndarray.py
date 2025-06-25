import warnings

from asdf.extension import Validator
from asdf.tags.core.ndarray import validate_datatype, validate_max_ndim, validate_ndim


def _warn_if_not_array(node, schema_property):
    # warn here for non-ndarray tags, in a major version bump we can
    # remove this and update the tags below to only match ndarrays
    if not getattr(node, "_tag", "").startswith("tag:stsci.edu:asdf/core/ndarray-"):
        warnings.warn(
            f"Use of the {schema_property} validator with non-ndarray tags is deprecated. "
            "Please define a custom validator for your tag",
            DeprecationWarning,
        )


class NdimValidator(Validator):
    schema_property = "ndim"
    tags = ["**"]

    def validate(self, expected_ndim, node, schema):
        _warn_if_not_array(node, self.schema_property)
        yield from validate_ndim(None, expected_ndim, node, schema)


class MaxNdimValidator(Validator):
    schema_property = "max_ndim"
    tags = ["**"]

    def validate(self, max_ndim, node, schema):
        _warn_if_not_array(node, self.schema_property)
        yield from validate_max_ndim(None, max_ndim, node, schema)


class DatatypeValidator(Validator):
    schema_property = "datatype"
    tags = ["**"]

    def validate(self, expected_datatype, node, schema):
        _warn_if_not_array(node, self.schema_property)
        yield from validate_datatype(None, expected_datatype, node, schema)
