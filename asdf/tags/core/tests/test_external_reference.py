from asdf._tests import _helpers as helpers
from asdf.tags.core.external_reference import ExternalArrayReference


def test_roundtrip_external_array(tmpdir):
    ref = ExternalArrayReference("./nonexistent.fits", 1, "np.float64", (100, 100))

    tree = {"nothere": ref}

    helpers.assert_roundtrip_tree(tree, tmpdir)
