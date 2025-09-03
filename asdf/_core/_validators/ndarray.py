from asdf.extension import Validator
from asdf.tags.core.ndarray import validate_datatype, validate_max_ndim, validate_ndim


class NdimValidator(Validator):
    schema_property = "ndim"
    tags = ["tag:stsci.edu:asdf/core/ndarray-*"]

    def validate(self, expected_ndim, node, schema):
        yield from validate_ndim(None, expected_ndim, node, schema)


class MaxNdimValidator(Validator):
    schema_property = "max_ndim"
    tags = ["tag:stsci.edu:asdf/core/ndarray-*"]

    def validate(self, max_ndim, node, schema):
        yield from validate_max_ndim(None, max_ndim, node, schema)


class DatatypeValidator(Validator):
    schema_property = "datatype"
    tags = ["tag:stsci.edu:asdf/core/ndarray-*"]

    def validate(self, expected_datatype, node, schema):
        yield from validate_datatype(None, expected_datatype, node, schema)
