import io

import pytest

from asdf import AsdfFile
from asdf.commands import list_tags


@pytest.mark.parametrize("display_classes", [True, False])
def test_parameter_combinations(display_classes):
    # Just confirming no errors:
    list_tags(display_classes)


def test_all_tags_present():
    iostream = io.StringIO()
    list_tags(iostream=iostream)
    iostream.seek(0)
    tags = {line.strip() for line in iostream.readlines()}

    af = AsdfFile()
    for tag in af.extension_manager._converters_by_tag:
        assert tag in tags
