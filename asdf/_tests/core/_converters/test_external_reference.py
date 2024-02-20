from asdf.tags.core.external_reference import ExternalArrayReference
from asdf.testing.helpers import roundtrip_object


def test_roundtrip_external_array(tmp_path):
    ref = ExternalArrayReference("./nonexistent.fits", 1, "np.float64", (100, 100))

    result = roundtrip_object(ref)

    assert result == ref
