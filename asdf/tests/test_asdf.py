import pytest

from asdf.asdf import AsdfFile
from asdf import config_context
from asdf.versioning import AsdfVersion


def test_asdf_file_version():
    with config_context() as config:
        config.default_version = "1.2.0"

        af = AsdfFile()
        assert af.version == AsdfVersion("1.2.0")
        assert af.version_string == "1.2.0"

        af = AsdfFile(version="1.3.0")
        assert af.version == AsdfVersion("1.3.0")
        assert af.version_string == "1.3.0"

        af = AsdfFile(version=AsdfVersion("1.3.0"))
        assert af.version == AsdfVersion("1.3.0")
        assert af.version_string == "1.3.0"

        with pytest.raises(ValueError):
            AsdfFile(version="0.5.4")

        with pytest.raises(ValueError):
            AsdfFile(version=AsdfVersion("0.5.4"))

        af = AsdfFile()

        af.version = "1.3.0"
        assert af.version == AsdfVersion("1.3.0")
        assert af.version_string == "1.3.0"

        af.version = AsdfVersion("1.4.0")
        assert af.version == AsdfVersion("1.4.0")
        assert af.version_string == "1.4.0"

        with pytest.raises(ValueError):
            af.version = "0.5.4"

        with pytest.raises(ValueError):
            af.version = AsdfVersion("2.5.4")

        af.version = "1.0.0"
        assert af.version_map["tags"]["tag:stsci.edu:asdf/core/asdf"] == "1.0.0"

        af.version = "1.2.0"
        assert af.version_map["tags"]["tag:stsci.edu:asdf/core/asdf"] == "1.1.0"
