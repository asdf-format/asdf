import warnings

import numpy as np

import asdf

__all__ = [
    "assert_tree_match",
]


def assert_tree_match(old_tree, new_tree):
    """
    Assert that two ASDF trees match.

    Parameters
    ----------
    old_tree : ASDF tree

    new_tree : ASDF tree
    """

    seen = set()
    ignore_keys = {"asdf_library", "history"}

    def recurse(old, new):
        if id(old) in seen or id(new) in seen:
            return

        seen.add(id(old))
        seen.add(id(new))

        if isinstance(old, dict) and isinstance(new, dict):
            assert {x for x in old if x not in ignore_keys} == {x for x in new if x not in ignore_keys}
            for key in old:
                if key not in ignore_keys:
                    recurse(old[key], new[key])
        elif isinstance(old, (list, tuple)) and isinstance(new, (list, tuple)):
            assert len(old) == len(new)
            for a, b in zip(old, new):
                recurse(a, b)
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
