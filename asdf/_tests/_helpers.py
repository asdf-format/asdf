import warnings

try:
    from astropy.coordinates import ICRS
except ImportError:
    ICRS = None

try:
    from astropy.coordinates.representation import CartesianRepresentation
except ImportError:
    CartesianRepresentation = None

try:
    from astropy.coordinates.representation import CartesianDifferential
except ImportError:
    CartesianDifferential = None

import numpy as np

import asdf

try:
    from pytest_remotedata.disable_internet import INTERNET_OFF
except ImportError:
    INTERNET_OFF = False


__all__ = [
    "assert_tree_match",
]


def assert_tree_match(old_tree, new_tree, ctx=None, funcname="assert_equal", ignore_keys=None):
    """
    Assert that two ASDF trees match.

    Parameters
    ----------
    old_tree : ASDF tree

    new_tree : ASDF tree

    ctx : ASDF file context
        Used to look up the set of types in effect.

    funcname : `str` or `callable`
        The name of a method on members of old_tree and new_tree that
        will be used to compare custom objects.  The default of
        ``assert_equal`` handles Numpy arrays.

    ignore_keys : list of str
        List of keys to ignore
    """
    seen = set()

    if ignore_keys is None:
        ignore_keys = ["asdf_library", "history"]
    ignore_keys = set(ignore_keys)

    def recurse(old, new):
        if id(old) in seen or id(new) in seen:
            return
        seen.add(id(old))
        seen.add(id(new))

        old_type = None
        new_type = None

        if (
            old_type is not None
            and new_type is not None
            and old_type is new_type
            and (callable(funcname) or hasattr(old_type, funcname))
        ):
            if callable(funcname):
                funcname(old, new)
            else:
                getattr(old_type, funcname)(old, new)

        elif isinstance(old, dict) and isinstance(new, dict):
            assert {x for x in old if x not in ignore_keys} == {x for x in new if x not in ignore_keys}
            for key in old:
                if key not in ignore_keys:
                    recurse(old[key], new[key])
        elif isinstance(old, (list, tuple)) and isinstance(new, (list, tuple)):
            assert len(old) == len(new)
            for a, b in zip(old, new):
                recurse(a, b)
        # The astropy classes CartesianRepresentation, CartesianDifferential,
        # and ICRS do not define equality in a way that is meaningful for unit
        # tests. We explicitly compare the fields that we care about in order
        # to enable our unit testing. It is possible that in the future it will
        # be necessary or useful to account for fields that are not currently
        # compared.
        elif CartesianRepresentation is not None and isinstance(old, CartesianRepresentation):
            assert old.x == new.x
            assert old.y == new.y
            assert old.z == new.z
        elif CartesianDifferential is not None and isinstance(old, CartesianDifferential):
            assert old.d_x == new.d_x
            assert old.d_y == new.d_y
            assert old.d_z == new.d_z
        elif ICRS is not None and isinstance(old, ICRS):
            assert old.ra == new.ra
            assert old.dec == new.dec
        elif all([isinstance(obj, (np.ndarray, asdf.tags.core.NDArrayType)) for obj in (old, new)]):
            with warnings.catch_warnings():
                # The oldest deps job tests against versions of numpy where this
                # testing function raised a FutureWarning but still functioned
                # as expected
                warnings.filterwarnings("ignore", category=FutureWarning)
                if old.dtype.fields:
                    if not new.dtype.fields:
                        msg = "arrays not equal"
                        raise AssertionError(msg)
                    for f in old.dtype.fields:
                        np.testing.assert_array_equal(old[f], new[f])
                else:
                    np.testing.assert_array_equal(old.__array__(), new.__array__())
        else:
            assert old == new

    recurse(old_tree, new_tree)
