import random

import pytest

import asdf
from asdf.testing import helpers
from asdf import constants
from asdf.tagged import TaggedDict


@pytest.fixture(autouse=True)
def set_random_seed():
    # Make sure tests are deterministic
    random.seed(0)


@pytest.mark.parametrize("sign", ["+", "-"])
@pytest.mark.parametrize(
    "value",
    [
        random.getrandbits(64),
        random.getrandbits(65),
        random.getrandbits(100),
        random.getrandbits(128),
        random.getrandbits(129),
        random.getrandbits(200),
    ],
)
def test_integer_roundtrip(sign, value):
    if sign == "-":
        value = -value

    result = helpers.roundtrip_object(value)

    assert result == value


def test_integer_representation(tmp_path):
    file_path = tmp_path / "integer.asdf"

    value = random.getrandbits(1000)
    with asdf.AsdfFile() as af:
        af["large_positive_integer"] = value
        af["large_negative_integer"] = -value
        af["normal_integer"] = constants.MAX_NUMBER
        af.write_to(file_path)

    with asdf.open(file_path) as af:
        assert af["large_positive_integer"] == value
        assert af["large_negative_integer"] == -value
        assert af["normal_integer"] == constants.MAX_NUMBER

    with asdf.open(file_path, _force_raw_types=True) as af:
        assert isinstance(af["normal_integer"], int)
        assert isinstance(af["large_positive_integer"], TaggedDict)
        assert isinstance(af["large_negative_integer"], TaggedDict)
