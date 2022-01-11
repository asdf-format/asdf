from asdf.core import ExternalArrayReference
from asdf.testing import helpers


def test_external_array_reference():
    ref = ExternalArrayReference("./nonexistant.fits", 1, "np.float64", (100, 100))

    result = helpers.roundtrip_object(ref)

    assert result == ref
