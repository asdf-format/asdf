import pytest

from asdf import CustomType, util
from asdf.exceptions import AsdfDeprecationWarning

from ._helpers import get_test_data_path

with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

    class CustomTestType(CustomType):
        """This class is intended to be inherited by custom types that are used
        purely for the purposes of testing. The methods ``from_tree_tagged`` and
        ``from_tree`` are implemented solely in order to avoid custom type
        conversion warnings.
        """

        @classmethod
        def from_tree_tagged(cls, tree, ctx):
            return cls.from_tree(tree.data, ctx)

        @classmethod
        def from_tree(cls, tree, ctx):
            return tree


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
