# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
import pytest

from asdf.tags.core.external_reference import ExternalArrayReference, ExternalArrayReferenceCollection
from asdf.tests import helpers


def test_roundtrip_external_array(tmpdir):
    ref = ExternalArrayReference("./nonexistant.fits", 1,
                                 "np.float64", (100, 100))

    tree = {'nothere': ref}

    helpers.assert_roundtrip_tree(tree, tmpdir)


@pytest.fixture
def earcollection():
    return ExternalArrayReferenceCollection(["./nonexistant.fits",
                                             "./nonexistant-1.fits"],
                                             1,
                                             "np.float64",
                                             (100, 100))


def test_roundtrip_external_array_collection(tmpdir, earcollection):
    tree = {'nothere': earcollection}

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_collection_to_references(tmpdir, earcollection):
    ears = earcollection.external_array_references
    assert len(earcollection) == len(ears) == 2

    for ear in ears:
      assert isinstance(ear, ExternalArrayReference)
      assert ear.target == earcollection.target
      assert ear.dtype == earcollection.dtype
      assert ear.shape == earcollection.shape


def test_collection_getitem(tmpdir, earcollection):
    assert isinstance(earcollection[0], ExternalArrayReferenceCollection)
    assert isinstance(earcollection[1], ExternalArrayReferenceCollection)
    assert len(earcollection[0]) == len(earcollection[1]) == 1
    assert earcollection[0:2] == earcollection
