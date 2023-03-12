from asdf.tags.core import Constant
from asdf.testing import helpers


def test_constant():
    constant = Constant("gardener")

    result = helpers.roundtrip_object(constant)

    assert result.value == constant.value
