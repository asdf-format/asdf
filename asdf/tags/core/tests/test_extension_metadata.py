import warnings

import pytest
import asdf
from asdf.tests import helpers


def test_old_format(recwarn):
    warnings.simplefilter("always")

    content = helpers.yaml_to_asdf("""
extension: !core/extension_metadata-1.0.0
  extension_class: asdf.extension.BuiltinExtension
  software: {name: asdf, version: 2.5.0}
""")

    with asdf.open(content) as af:
        extension = af.tree["extension"]
        assert isinstance(extension, asdf.tags.core.ExtensionMetadata)
        assert extension.extension_class == "asdf.extension.BuiltinExtension"
        assert isinstance(extension.package, asdf.tags.core.Software)
        assert extension.package["name"] == "asdf"
        assert extension.package["version"] == "2.5.0"
        software = extension.software
        assert isinstance(software, asdf.tags.core.Software)
        assert software["name"] == "asdf"
        assert software["version"] == "2.5.0"

    # One warning for opening a file in the old format, another for
    # accessing the 'software' property:
    assert len(recwarn) == 2
    assert recwarn.pop(asdf.exceptions.AsdfDeprecationWarning)
    assert recwarn.pop(asdf.exceptions.AsdfDeprecationWarning)


def test_new_format(recwarn):
    warnings.simplefilter("always")

    content = helpers.yaml_to_asdf("""
extension: !core/extension_metadata-1.0.0
  extension_class: asdf.extension.BuiltinExtension
  package: !core/software-1.0.0 {name: asdf, version: 2.5.0}
""")

    with asdf.open(content) as af:
        extension = af.tree["extension"]
        assert isinstance(extension, asdf.tags.core.ExtensionMetadata)
        assert extension.extension_class == "asdf.extension.BuiltinExtension"
        assert isinstance(extension.package, asdf.tags.core.Software)
        assert extension.package["name"] == "asdf"
        assert extension.package["version"] == "2.5.0"
        software = extension.software
        assert isinstance(software, asdf.tags.core.Software)
        assert software["name"] == "asdf"
        assert software["version"] == "2.5.0"

    # One warning for accessing the 'software' property:
    assert len(recwarn) == 1
    assert recwarn.pop(asdf.exceptions.AsdfDeprecationWarning)
