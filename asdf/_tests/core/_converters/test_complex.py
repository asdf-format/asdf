import re

import pytest

import asdf
from asdf.testing import helpers


def make_complex_asdf(string):
    yaml = f"""
a: !core/complex-1.0.0
  {string}
    """

    return helpers.yaml_to_asdf(yaml)


@pytest.mark.parametrize(
    "invalid",
    [
        "3 + 4i",
        "3+-4i",
        "3-+4i",
        "3i+4i",
        "X3+4iX",
        "3+X4i",
        "3+4",
        "3i+43+4z",
        "3.+4i",
        "3+4.i",
        "3e-4.0+4i",
        "3+4e4.0i",
        "",
    ],
)
def test_invalid_complex(invalid):
    with pytest.raises(asdf.ValidationError), asdf.open(make_complex_asdf(invalid)):
        pass


@pytest.mark.parametrize(
    "valid",
    [
        "3+4j",
        "(3+4j)",
        ".3+4j",
        "3+.4j",
        "3e10+4j",
        "3e-10+4j",
        "3+4e10j",
        "3.0+4j",
        "3+4.0j",
        "3.0+4.0j",
        "3+4e-10j",
        "3+4J",
        "3+4i",
        "3+4I",
        "inf",
        "inf+infj",
        "inf+infi",
        "infj",
        "infi",
        "INFi",
        "INFI",
        "3+infj",
        "inf+4j",
    ],
)
def test_valid_complex(valid):
    with asdf.open(make_complex_asdf(valid)) as af:
        assert af.tree["a"] == complex(re.sub(r"[iI]$", r"j", valid))


@pytest.mark.parametrize(
    "valid",
    ["nan", "nan+nanj", "nan+nani", "nanj", "nani", "NANi", "NANI", "3+nanj", "nan+4j"],
)
def test_valid_nan_complex(valid):
    with asdf.open(make_complex_asdf(valid)):
        pass


def test_roundtrip(tmp_path):
    values = {
        "a": 0 + 0j,
        "b": 1 + 1j,
        "c": -1 + 1j,
        "d": -1 - 1j,
    }

    fn = tmp_path / "test.asdf"
    asdf.AsdfFile({"values": values}).write_to(fn)
    with asdf.open(fn) as af:
        result = af["values"]
        assert len(values) == len(result)
        for key, value in values.items():
            assert result[key] == value
