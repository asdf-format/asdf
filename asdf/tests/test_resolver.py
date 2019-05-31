# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import pytest

from asdf.resolver import Resolver, ResolverChain
from asdf.exceptions import AsdfDeprecationWarning

def test_resolver_no_mappings():
    r = Resolver([], "test")
    assert r("united_states:maryland:baltimore") == "united_states:maryland:baltimore"


def test_resolver_tuple_mapping():
    r = Resolver([("united_states:", "earth:{test}")], "test")
    assert r("united_states:maryland:baltimore") == "earth:united_states:maryland:baltimore"

    r = Resolver([("united_states:", "{test_prefix}texas:houston")], "test")
    assert r("united_states:maryland:baltimore") == "united_states:texas:houston"

    r = Resolver([("united_states:", "{test_suffix}:hampden")], "test")
    assert r("united_states:maryland:baltimore") == "maryland:baltimore:hampden"


def test_resolver_callable_mapping():
    r = Resolver([lambda inp: "nowhere"], "test")
    assert r("united_states:maryland:baltimore") == "nowhere"


def test_resolver_multiple_mappings():
    r = Resolver([
        ("united_states:", "unknown_region:{test_suffix}"),
        ("united_states:maryland:", "mid_atlantic:maryland:{test_suffix}")
        ], "test")
    # Should choose the mapping with the longest matched prefix:
    assert r("united_states:maryland:baltimore") == "mid_atlantic:maryland:baltimore"

    r = Resolver([
        ("united_states:", "unknown_region:{test_suffix}"),
        lambda inp: "nowhere",
        ("united_states:maryland:", "mid_atlantic:maryland:{test_suffix}")
        ], "test")
    # Should prioritize the mapping offered by the callable:
    assert r("united_states:maryland:baltimore") == "nowhere"

    r = Resolver([
        ("united_states:", "unknown_region:{test_suffix}"),
        lambda inp: None,
        ("united_states:maryland:", "mid_atlantic:maryland:{test_suffix}")
        ], "test")
    # None from the callable is a signal that it can't handle the input,
    # so we should fall back to the longest matched prefix:
    assert r("united_states:maryland:baltimore") == "mid_atlantic:maryland:baltimore"


def test_resolver_non_prefix():
    r = Resolver([("maryland:", "shouldn't happen")], "test")
    assert r("united_states:maryland:baltimore") == "united_states:maryland:baltimore"


def test_resolver_invalid_mapping():
    with pytest.raises(ValueError):
        Resolver([("foo",)], "test")

    with pytest.raises(ValueError):
        Resolver([12], "test")


def test_resolver_hash_and_equals():
    r1 = Resolver([("united_states:", "earth:{test}")], "test")
    r2 = Resolver([("united_states:", "earth:{test}")], "test")
    r3 = Resolver([("united_states:", "{test}:hampden")], "test")

    assert hash(r1) == hash(r2)
    assert r1 == r2

    assert hash(r1) != hash(r3)
    assert r1 != r3


def test_resolver_add_mapping_deprecated():
    r = Resolver([], "test")
    with pytest.warns(AsdfDeprecationWarning):
        r.add_mapping([("united_states:", "earth:{test}")], "test")


def test_resolver_chain():
    r1 = Resolver([("maryland:", "united_states:{test}")], "test")
    r2 = Resolver([("united_states:", "earth:{test}")], "test")

    chain = ResolverChain(r1, r2)

    assert chain("maryland:baltimore") == "earth:united_states:maryland:baltimore"


def test_resolver_chain_hash_and_equals():
    r1 = Resolver([("united_states:", "earth:{test}")], "test")
    r2 = Resolver([("united_states:", "earth:{test}")], "test")
    r3 = Resolver([("united_states:", "{test}:hampden")], "test")

    c1 = ResolverChain(r1, r3)
    c2 = ResolverChain(r2, r3)
    c3 = ResolverChain(r1, r2)

    assert hash(c1) == hash(c2)
    assert c1 == c2

    assert hash(c1) != hash(c3)
    assert c1 != c3
