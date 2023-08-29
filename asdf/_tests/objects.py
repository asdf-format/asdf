from asdf import util

from ._helpers import get_test_data_path


class CustomExtension:
    """
    This is the base class that is used for extensions for custom tag
    classes that exist only for the purposes of testing.
    """

    @property
    def types(self):
        return []

    @property
    def tag_mapping(self):
        return [("tag:nowhere.org:custom", "http://nowhere.org/schemas/custom{tag_suffix}")]

    @property
    def url_mapping(self):
        return [
            ("http://nowhere.org/schemas/custom/", util.filepath_to_url(get_test_data_path("")) + "/{url_suffix}.yaml"),
        ]
