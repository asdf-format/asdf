import pytest

import asdf

from .helpers import get_test_data_path


@pytest.mark.filterwarnings("ignore:AsdfDeprecationWarning")
def test_2_5_0_extension_metadata():
    with asdf.open(get_test_data_path("asdf-2.5.0-empty.asdf")) as af:
        extension = af.tree["history"]["extensions"][0]
        assert isinstance(extension.package, asdf.tags.core.Software)
        assert extension.package["name"] == "asdf"
        assert extension.package["version"] == "2.5.0"
