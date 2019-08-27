from asdf import extension
from asdf.tests import CustomTestType


class LabelMapperTestType(CustomTestType):
    version = '1.0.0'
    name = 'transform/label_mapper'


class RegionsSelectorTestType(CustomTestType):
    version = '1.0.0'
    name = 'transform/regions_selector'


class TestExtension(extension.BuiltinExtension):
    """This class defines an extension that represents tags whose
    implementations current reside in other repositories (such as GWCS) but
    whose schemas are defined in ASDF. This provides a workaround for schema
    validation testing since we want to pass without warnings, but the fact
    that these tag classes are not defined within ASDF means that warnings
    occur unless this extension is used. Eventually these schemas may be moved
    out of ASDF and into other repositories, or ASDF will potentially provide
    abstract base classes for the tag implementations.
    """
    @property
    def types(self):
        return [LabelMapperTestType, RegionsSelectorTestType]

    @property
    def tag_mapping(self):
        return [('tag:stsci.edu:asdf',
                 'http://stsci.edu/schemas/asdf{tag_suffix}')]
