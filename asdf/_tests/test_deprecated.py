import pytest

import asdf


def test_resolver_deprecation():

    def resolver(uri):
        return uri

    with pytest.warns(DeprecationWarning, match="resolver is deprecated"):
        asdf.schema.load_schema("http://stsci.edu/schemas/asdf/asdf-schema-1.0.0", resolver=resolver)
