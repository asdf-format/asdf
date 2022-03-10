import io

import pytest

from asdf import get_config

from .. import list_tags


@pytest.mark.parametrize("display_classes", [True, False])
def test_parameter_combinations(display_classes):
    # Just confirming no errors:
    list_tags(display_classes)


def test_all_tags_present():
    iostream = io.StringIO()
    list_tags(iostream=iostream)
    iostream.seek(0)
    tags = {line.strip() for line in iostream.readlines()}

    type_index = get_config().extension_list.type_index
    extension_manager = get_config().get_extension_manager(get_config().default_version)

    for tag in type_index._type_by_tag:
        assert tag in tags
    for tag in extension_manager._converters_by_tag:
        assert tag in tags
