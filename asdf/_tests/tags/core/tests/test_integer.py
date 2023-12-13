import random

import pytest

import asdf
from asdf import IntegerType
from asdf.testing.helpers import roundtrip_object

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
def test_integer_value(value, sign):
    if sign == "-":
        value = -value

    integer = IntegerType(value)
    assert integer == roundtrip_object(integer)


@pytest.mark.parametrize("inline", [False, True])
def test_integer_storage(tmp_path, inline):
    tmpfile = str(tmp_path / "integer.asdf")

    kwargs = {}
    if inline:
        kwargs["storage_type"] = "inline"

    random.seed(0)
    value = random.getrandbits(1000)
    tree = {"integer": IntegerType(value, **kwargs)}

    with asdf.AsdfFile(tree) as af:
        af.write_to(tmpfile)

    tree = asdf.util.load_yaml(tmpfile, tagged=True)
    if inline:
        assert "source" not in tree["integer"]["words"]
        assert "data" in tree["integer"]["words"]
    else:
        assert "source" in tree["integer"]["words"]
        assert "data" not in tree["integer"]["words"]

    assert "string" in tree["integer"]
    assert tree["integer"]["string"] == str(value)


def test_integer_conversion():
    random.seed(0)
    value = random.getrandbits(1000)

    integer = asdf.IntegerType(value)
    assert integer == value
    assert int(integer) == int(value)
    assert float(integer) == float(value)
