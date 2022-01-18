import numpy as np

from asdf.extension import Validator
from asdf.exceptions import ValidationError
from asdf.tags.core.ndarray import (
    asdf_datatype_to_numpy_dtype,
    inline_data_asarray,
    numpy_dtype_to_asdf_datatype,
)


class NdimValidator(Validator):
    schema_property = "ndim"
    tags = ["tag:stsci.edu:asdf/core/ndarray-*"]

    def validate(self, expected_ndim, node, schema):
        actual_ndim = _get_ndim(node)

        if actual_ndim != expected_ndim:
            yield ValidationError(
                f"Wrong number of dimensions: Expected {expected_ndim}, got {actual_ndim}"
            )


class MaxNdimValidator(Validator):
    schema_property = "max_ndim"
    tags = ["tag:stsci.edu:asdf/core/ndarray-*"]

    def validate(self, max_ndim, node, schema):
        ndim = _get_ndim(node)

        if ndim > max_ndim:
            yield ValidationError(
                f"Wrong number of dimensions: Expected max of {max_ndim}, got {ndim}"
            )


class DatatypeValidator(Validator):
    schema_property = "datatype"
    tags = ["tag:stsci.edu:asdf/core/ndarray-*"]

    def validate(self, expected_datatype, node, schema):
        if "datatype" in node:
            actual_datatype = node["datatype"]
        elif "data" in node:
            array = inline_data_asarray(node["data"])
            actual_datatype, _ = numpy_dtype_to_asdf_datatype(array.dtype)
        else:
            raise ValidationError("Not an valid ndarray")

        if actual_datatype == expected_datatype:
            return

        if schema.get("exact_datatype", False):
            yield ValidationError(
                f"Expected datatype '{expected_datatype}', got '{actual_datatype}'"
            )

        expected_np_datatype = asdf_datatype_to_numpy_dtype(expected_datatype)
        actual_np_datatype = asdf_datatype_to_numpy_dtype(actual_datatype)

        if not expected_np_datatype.fields:
            if actual_np_datatype.fields:
                yield ValidationError(
                    f"Expected scalar datatype '{expected_datatype}', got '{actual_datatype}'"
                )

            if not np.can_cast(actual_np_datatype, expected_np_datatype, "safe"):
                yield ValidationError(
                    f"Cannot safely cast from '{actual_datatype}' to '{expected_datatype}'"
                )
        else:
            if not actual_np_datatype.fields:
                yield ValidationError(
                    f"Expected structured datatype '{expected_datatype}', got '{actual_datatype}'"
                )

            if len(actual_np_datatype.fields) != len(expected_np_datatype.fields):
                yield ValidationError(
                    "Mismatch in number of columns: "
                    f"Expected {len(expected_datatype)}, got {len(actual_datatype)}"
                )

            for i in range(len(actual_np_datatype.fields)):
                actual_type = actual_np_datatype[i]
                expected_type = expected_np_datatype[i]
                if not np.can_cast(actual_type, expected_type, "safe"):
                    yield ValidationError(
                        "Cannot safely cast to expected datatype: "
                        f"Expected {numpy_dtype_to_asdf_datatype(expected_type)[0]}, "
                        f"got {numpy_dtype_to_asdf_datatype(actual_type)[0]}"
                    )


def _get_ndim(node):
    if "shape" in node:
        return len(node["shape"])
    elif "data" in node:
        array = inline_data_asarray(node["data"])
        return array.ndim
    else:
        raise ValidationError("Not a valid ndarray")
