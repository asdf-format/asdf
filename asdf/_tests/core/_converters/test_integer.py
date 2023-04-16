import random

import pytest

import asdf
from asdf import constants
from asdf.exceptions import AsdfDeprecationWarning
from asdf.tagged import TaggedDict
from asdf.tags.core import IntegerType
from asdf.testing import helpers


@pytest.fixture(autouse=True)
def set_random_seed():
    # Make sure tests are deterministic
    random.seed(0)


@pytest.mark.parametrize("sign", ["+", "-"])
@pytest.mark.parametrize(
    "value",
    [
        12354295463861780261,
        34350970557135724229,
        111486802101863275720740618121,
        120141276809567679697787158724268622606,
        87364497025259279754758976379453629691,
        537931524073525845224042128940663068627838630773304450902654,
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
        af["normal_positive_integer"] = constants.MAX_NUMBER
        af["normal_negative_integer"] = constants.MIN_NUMBER
        af.write_to(file_path)

    with asdf.open(file_path) as af:
        assert af["large_positive_integer"] == value
        assert af["large_negative_integer"] == -value
        assert af["normal_positive_integer"] == constants.MAX_NUMBER
        assert af["normal_negative_integer"] == constants.MIN_NUMBER

    with asdf.open(file_path, _force_raw_types=True) as af:
        assert isinstance(af["large_positive_integer"], TaggedDict)
        assert isinstance(af["large_negative_integer"], TaggedDict)
        assert isinstance(af["normal_positive_integer"], int)
        assert isinstance(af["normal_negative_integer"], int)


def test_integer_type(tmp_path):
    file_path = tmp_path / "integer.asdf"

    with pytest.warns(AsdfDeprecationWarning, match=".*IntegerType is deprecated.*"):
        value = IntegerType(random.getrandbits(1000))

    with asdf.AsdfFile() as af:
        af["integer_type"] = value
        af.write_to(file_path)

    with asdf.open(file_path) as af:
        assert af["integer_type"] == value
