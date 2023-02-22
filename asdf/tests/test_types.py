import io
from fractions import Fraction

import pytest

import asdf
from asdf import _types as types
from asdf import util, versioning
from asdf.exceptions import AsdfConversionWarning, AsdfDeprecationWarning, AsdfWarning
from asdf.extension import _legacy

from . import _helpers as helpers
from .objects import CustomExtension, CustomTestType

TEST_DATA_PATH = str(helpers.get_test_data_path(""))


class Fractional2dCoord:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class FractionWithInverse(Fraction):
    def __init__(self, *args, **kwargs):
        self._inverse = None

    @property
    def inverse(self):
        return self._inverse

    @inverse.setter
    def inverse(self, value):
        self._inverse = value


with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

    class FractionWithInverseType(asdf.CustomType):
        name = "fraction_with_inverse"
        organization = "nowhere.org"
        version = (1, 0, 0)
        standard = "custom"
        types = [FractionWithInverse]

        @classmethod
        def to_tree(cls, node, ctx):
            return {"numerator": node.numerator, "denominator": node.denominator, "inverse": node.inverse}

        @classmethod
        def from_tree(cls, tree, ctx):
            result = FractionWithInverse(tree["numerator"], tree["denominator"])
            yield result
            result.inverse = tree["inverse"]


class FractionWithInverseExtension(CustomExtension):
    @property
    def types(self):
        return [FractionWithInverseType]

    @property
    def tag_mapping(self):
        return [("tag:nowhere.org:custom", "http://nowhere.org/schemas/custom{tag_suffix}")]

    @property
    def url_mapping(self):
        return [("http://nowhere.org/schemas/custom/", util.filepath_to_url(TEST_DATA_PATH) + "/{url_suffix}.yaml")]


def fractiontype_factory():
    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class FractionType(types.CustomType):
            name = "fraction"
            organization = "nowhere.org"
            version = (1, 0, 0)
            standard = "custom"
            types = [Fraction]
            handle_dynamic_subclasses = True

            @classmethod
            def to_tree(cls, node, ctx):
                return [node.numerator, node.denominator]

            @classmethod
            def from_tree(cls, tree, ctx):
                return Fraction(tree[0], tree[1])

    return FractionType


def fractional2dcoordtype_factory():
    FractionType = fractiontype_factory()  # noqa: N806

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class Fractional2dCoordType(types.CustomType):
            name = "fractional_2d_coord"
            organization = "nowhere.org"
            standard = "custom"
            version = (1, 0, 0)
            types = [Fractional2dCoord]

            @classmethod
            def to_tree(cls, node, ctx):
                return {"x": node.x, "y": node.y}

            @classmethod
            def from_tree(cls, tree, ctx):
                return Fractional2dCoord(tree["x"], tree["y"])

    class Fractional2dCoordExtension(CustomExtension):
        @property
        def types(self):
            return [FractionType, Fractional2dCoordType]

    return FractionType, Fractional2dCoordType, Fractional2dCoordExtension


def test_custom_tag():
    FractionType = fractiontype_factory()  # noqa: N806

    class FractionExtension(CustomExtension):
        @property
        def types(self):
            return [FractionType]

    class FractionCallable(FractionExtension):
        @property
        def tag_mapping(self):
            def check(tag):
                prefix = "tag:nowhere.org:custom"
                if tag.startswith(prefix):
                    return "http://nowhere.org/schemas/custom" + tag[len(prefix) :]

                return None

            return [check]

    yaml = """
a: !<tag:nowhere.org:custom/fraction-1.0.0>
  [2, 3]
b: !core/complex-1.0.0
  0j
    """

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.open(buff, extensions=FractionExtension()) as ff:
        assert ff.tree["a"] == Fraction(2, 3)

        buff = io.BytesIO()
        ff.write_to(buff)

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.open(buff, extensions=FractionCallable()) as ff:
        assert ff.tree["a"] == Fraction(2, 3)

        buff = io.BytesIO()
        ff.write_to(buff)
        buff.close()


def test_version_mismatch():
    yaml = """
a: !core/complex-42.0.0
  0j
    """

    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(AsdfConversionWarning, match=r"tag:stsci.edu:asdf/core/complex"), asdf.open(
        buff,
        ignore_version_mismatch=False,
    ) as ff:
        assert isinstance(ff.tree["a"], complex)

    # Make sure warning is repeatable
    buff.seek(0)
    with pytest.warns(AsdfConversionWarning, match=r"tag:stsci.edu:asdf/core/complex"), asdf.open(
        buff,
        ignore_version_mismatch=False,
    ) as ff:
        assert isinstance(ff.tree["a"], complex)

    # Make sure the warning does not occur if it is being ignored (default)
    buff.seek(0)
    with helpers.assert_no_warnings(AsdfConversionWarning), asdf.open(buff) as ff:
        assert isinstance(ff.tree["a"], complex)

    # If the major and minor match, but the patch doesn't, there
    # should still be a warning.
    yaml = """
a: !core/complex-1.0.1
  0j
    """

    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(AsdfConversionWarning, match=r"tag:stsci.edu:asdf/core/complex"), asdf.open(
        buff,
        ignore_version_mismatch=False,
    ) as ff:
        assert isinstance(ff.tree["a"], complex)


def test_version_mismatch_file(tmp_path):
    testfile = str(tmp_path / "mismatch.asdf")
    yaml = """
a: !core/complex-42.0.0
  0j
    """

    buff = helpers.yaml_to_asdf(yaml)
    with open(testfile, "wb") as handle:
        handle.write(buff.read())

    expected_uri = util.filepath_to_url(str(testfile))

    with pytest.warns(AsdfConversionWarning, match=r"tag:stsci.edu:asdf/core/complex"), asdf.open(
        testfile,
        ignore_version_mismatch=False,
    ) as ff:
        assert ff._fname == expected_uri
        assert isinstance(ff.tree["a"], complex)


def test_version_mismatch_with_supported_versions():
    """Make sure that defining the supported_versions field eliminates
    the schema mismatch warning."""

    class CustomFlow:
        pass

    class CustomFlowType(CustomTestType):
        version = "1.1.0"
        supported_versions = ["1.0.0", "1.1.0"]
        name = "custom_flow"
        organization = "nowhere.org"
        standard = "custom"
        types = [CustomFlow]

    class CustomFlowExtension(CustomExtension):
        @property
        def types(self):
            return [CustomFlowType]

    yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.0.0>
    c: 100
    d: 3.14
"""
    buff = helpers.yaml_to_asdf(yaml)
    with helpers.assert_no_warnings():
        asdf.open(buff, ignore_version_mismatch=False, extensions=CustomFlowExtension())


def test_versioned_writing(monkeypatch):
    from asdf.tags.core.complex import ComplexType

    # Create a bogus version map
    monkeypatch.setitem(
        versioning._version_map,
        "42.0.0",
        {
            "FILE_FORMAT": "42.0.0",
            "YAML_VERSION": "1.1",
            "tags": {"tag:stsci.edu:asdf/core/complex": "42.0.0", "tag:stscu.edu:asdf/core/asdf": "1.0.0"},
            # We need to insert these explicitly since we're monkeypatching
            "core": {"tag:stsci.edu:asdf/core/complex": "42.0.0", "tag:stscu.edu:asdf/core/asdf": "1.0.0"},
            "standard": {},
        },
    )

    # Add bogus version to supported versions
    monkeypatch.setattr(
        versioning,
        "supported_versions",
        [*versioning.supported_versions, versioning.AsdfVersion("42.0.0")],
    )

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class FancyComplexType(types.CustomType):
            name = "core/complex"
            organization = "stsci.edu"
            standard = "asdf"
            version = (42, 0, 0)
            types = [complex]

            @classmethod
            def to_tree(cls, node, ctx):
                return ComplexType.to_tree(node, ctx)

            @classmethod
            def from_tree(cls, tree, ctx):
                return ComplexType.from_tree(tree, ctx)

    class FancyComplexExtension:
        @property
        def types(self):
            return [FancyComplexType]

        @property
        def tag_mapping(self):
            return []

        @property
        def url_mapping(self):
            return [
                (
                    "http://stsci.edu/schemas/asdf/core/complex-42.0.0",
                    util.filepath_to_url(TEST_DATA_PATH) + "/complex-42.0.0.yaml",
                ),
            ]

    tree = {"a": complex(0, -1)}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree, version="42.0.0", extensions=[FancyComplexExtension()])
    ff.write_to(buff)

    assert b"complex-42.0.0" in buff.getvalue()


def test_longest_match():
    class FancyComplexExtension:
        @property
        def types(self):
            return []

        @property
        def tag_mapping(self):
            return []

        @property
        def url_mapping(self):
            return [("http://stsci.edu/schemas/asdf/core/", "FOOBAR/{url_suffix}")]

    extension_list = _legacy.AsdfExtensionList([_legacy.BuiltinExtension(), FancyComplexExtension()])

    assert extension_list.url_mapping("http://stsci.edu/schemas/asdf/core/asdf-1.0.0") == "FOOBAR/asdf-1.0.0"
    assert (
        extension_list.url_mapping("http://stsci.edu/schemas/asdf/transform/transform-1.0.0")
        != "FOOBAR/transform-1.0.0"
    )


def test_module_versioning():
    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class NoModuleType(types.CustomType):
            # It seems highly unlikely that this would be a real module
            requires = ["qkjvqdja"]

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class HasCorrectPytest(types.CustomType):
            # This means it requires 1.0.0 or greater, so it should succeed
            requires = ["pytest-1.0.0"]

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class DoesntHaveCorrectPytest(types.CustomType):
            requires = ["pytest-91984.1.7"]

    nmt = NoModuleType()
    hcp = HasCorrectPytest()
    # perhaps an unfortunate acroynm
    dhcp = DoesntHaveCorrectPytest()

    assert nmt.has_required_modules is False
    assert hcp.has_required_modules is True
    assert dhcp.has_required_modules is False


def test_undefined_tag():
    # This tests makes sure that ASDF still returns meaningful structured data
    # even when it encounters a schema tag that it does not specifically
    # implement as an extension
    from numpy import array

    yaml = """
undefined_data:
  !<tag:nowhere.org:custom/undefined_tag-1.0.0>
    - 5
    - {'message': 'there is no tag'}
    - !core/ndarray-1.0.0
      [[1, 2, 3], [4, 5, 6]]
    - !<tag:nowhere.org:custom/also_undefined-1.3.0>
        - !core/ndarray-1.0.0 [[7],[8],[9],[10]]
        - !core/complex-1.0.0 3.14j
"""
    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(Warning) as warning:
        afile = asdf.open(buff)
        missing = afile.tree["undefined_data"]

    assert missing[0] == 5
    assert missing[1] == {"message": "there is no tag"}
    assert (missing[2] == array([[1, 2, 3], [4, 5, 6]])).all()
    assert (missing[3][0] == array([[7], [8], [9], [10]])).all()
    assert missing[3][1] == 3.14j

    # There are two undefined tags, so we expect two warnings
    # filter out only AsdfConversionWarning
    warning = [w for w in warning if w.category == AsdfConversionWarning]
    assert len(warning) == 2
    for i, tag in enumerate(["also_undefined-1.3.0", "undefined_tag-1.0.0"]):
        assert (
            str(warning[i].message)
            == f"tag:nowhere.org:custom/{tag} is not recognized, converting to raw Python data structure"
        )

    # Make sure no warning occurs if explicitly ignored
    buff.seek(0)
    with helpers.assert_no_warnings():
        afile = asdf.open(buff, ignore_unrecognized_tag=True)


def test_newer_tag():
    """
    This test simulates a scenario where newer versions of CustomFlow
    provides different keyword parameters that the older schema and tag class
    do not account for. We want to test whether ASDF can handle this problem
    gracefully and still provide meaningful data as output. The test case is
    fairly contrived but we want to test whether ASDF can handle backwards
    compatibility even when an explicit tag class for different versions of a
    schema is not available.
    """

    class CustomFlow:
        def __init__(self, c=None, d=None):
            self.c = c
            self.d = d

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class CustomFlowType(types.CustomType):
            version = "1.1.0"
            name = "custom_flow"
            organization = "nowhere.org"
            standard = "custom"
            types = [CustomFlow]

            @classmethod
            def from_tree(cls, tree, ctx):
                kwargs = {}
                for name in tree:
                    kwargs[name] = tree[name]
                return CustomFlow(**kwargs)

            @classmethod
            def to_tree(cls, data, ctx):
                return {"c": data.c, "d": data.d}

    class CustomFlowExtension(CustomExtension):
        @property
        def types(self):
            return [CustomFlowType]

    new_yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.1.0>
    c: 100
    d: 3.14
"""
    new_buff = helpers.yaml_to_asdf(new_yaml)
    new_data = asdf.open(new_buff, extensions=CustomFlowExtension())
    assert type(new_data.tree["flow_thing"]) == CustomFlow

    old_yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.0.0>
    a: 100
    b: 3.14
"""
    old_buff = helpers.yaml_to_asdf(old_yaml)
    # We expect this warning since it will not be possible to convert version
    # 1.0.0 of CustomFlow to a CustomType (by design, for testing purposes).
    with pytest.warns(AsdfConversionWarning, match=r"Failed to convert tag:nowhere.org:custom/custom_flow-1.0.0"):
        asdf.open(old_buff, extensions=CustomFlowExtension())


def test_incompatible_version_check():
    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class TestType0(types.CustomType):
            supported_versions = versioning.AsdfSpec(">=1.2.0")

    assert TestType0.incompatible_version("1.1.0") is True
    assert TestType0.incompatible_version("1.2.0") is False
    assert TestType0.incompatible_version("2.0.1") is False

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class TestType1(types.CustomType):
            supported_versions = versioning.AsdfVersion("1.0.0")

    assert TestType1.incompatible_version("1.0.0") is False
    assert TestType1.incompatible_version("1.1.0") is True

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class TestType2(types.CustomType):
            supported_versions = "1.0.0"

    assert TestType2.incompatible_version("1.0.0") is False
    assert TestType2.incompatible_version("1.1.0") is True

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class TestType3(types.CustomType):
            # This doesn't make much sense, but it's just for the sake of example
            supported_versions = ["1.0.0", versioning.AsdfSpec(">=2.0.0")]

    assert TestType3.incompatible_version("1.0.0") is False
    assert TestType3.incompatible_version("1.1.0") is True
    assert TestType3.incompatible_version("2.0.0") is False
    assert TestType3.incompatible_version("2.0.1") is False

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class TestType4(types.CustomType):
            supported_versions = ["1.0.0", versioning.AsdfVersion("1.1.0")]

    assert TestType4.incompatible_version("1.0.0") is False
    assert TestType4.incompatible_version("1.0.1") is True
    assert TestType4.incompatible_version("1.1.0") is False
    assert TestType4.incompatible_version("1.1.1") is True

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class TestType5(types.CustomType):
            supported_versions = [versioning.AsdfSpec("<1.0.0"), versioning.AsdfSpec(">=2.0.0")]

    assert TestType5.incompatible_version("0.9.9") is False
    assert TestType5.incompatible_version("2.0.0") is False
    assert TestType5.incompatible_version("2.0.1") is False
    assert TestType5.incompatible_version("1.0.0") is True
    assert TestType5.incompatible_version("1.1.0") is True

    with pytest.raises(ValueError, match=r"Invalid version string: .*"), pytest.warns(
        AsdfDeprecationWarning,
        match=r".*subclasses the deprecated CustomType.*",
    ):

        class TestType6(types.CustomType):
            supported_versions = "blue"

    with pytest.raises(ValueError, match=r"Invalid version string: .*"), pytest.warns(
        AsdfDeprecationWarning,
        match=r".*subclasses the deprecated CustomType.*",
    ):

        class TestType7(types.CustomType):
            supported_versions = ["1.1.0", "2.2.0", "blue"]


def test_supported_versions():
    class CustomFlow:
        def __init__(self, c=None, d=None):
            self.c = c
            self.d = d

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class CustomFlowType(types.CustomType):
            version = "1.1.0"
            supported_versions = [(1, 0, 0), versioning.AsdfSpec(">=1.1.0")]
            name = "custom_flow"
            organization = "nowhere.org"
            standard = "custom"
            types = [CustomFlow]

            @classmethod
            def from_tree(cls, tree, ctx):
                # Convert old schema to new CustomFlow type
                if cls.version == "1.0.0":
                    return CustomFlow(c=tree["a"], d=tree["b"])

                return CustomFlow(**tree)

            @classmethod
            def to_tree(cls, data, ctx):
                if cls.version == "1.0.0":
                    return {"a": data.c, "b": data.d}

                return {"c": data.c, "d": data.d}

    class CustomFlowExtension(CustomExtension):
        @property
        def types(self):
            return [CustomFlowType]

    new_yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.1.0>
    c: 100
    d: 3.14
"""
    old_yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.0.0>
    a: 100
    b: 3.14
"""
    new_buff = helpers.yaml_to_asdf(new_yaml)
    new_data = asdf.open(new_buff, extensions=CustomFlowExtension())
    assert type(new_data.tree["flow_thing"]) == CustomFlow

    old_buff = helpers.yaml_to_asdf(old_yaml)
    old_data = asdf.open(old_buff, extensions=CustomFlowExtension())
    assert type(old_data.tree["flow_thing"]) == CustomFlow


def test_unsupported_version_warning():
    class CustomFlow:
        pass

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class CustomFlowType(types.CustomType):
            version = "1.0.0"
            supported_versions = [(1, 0, 0)]
            name = "custom_flow"
            organization = "nowhere.org"
            standard = "custom"
            types = [CustomFlow]

    class CustomFlowExtension(CustomExtension):
        @property
        def types(self):
            return [CustomFlowType]

    yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.1.0>
    c: 100
    d: 3.14
"""
    buff = helpers.yaml_to_asdf(yaml)

    with pytest.warns(
        AsdfConversionWarning,
        match=r"Version 1.1.0 of tag:nowhere.org:custom/custom_flow is not compatible",
    ):
        asdf.open(buff, extensions=CustomFlowExtension())


def test_tag_without_schema(tmp_path):
    tmpfile = str(tmp_path / "foo.asdf")

    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class FooType(types.CustomType):
            name = "foo"

            def __init__(self, a, b):
                self.a = a
                self.b = b

            @classmethod
            def from_tree(cls, tree, ctx):
                return cls(tree["a"], tree["b"])

            @classmethod
            def to_tree(cls, node, ctx):
                return {"a": node.a, "b": node.b}

            def __eq__(self, other):
                return self.a == other.a and self.b == other.b

    class FooExtension:
        @property
        def types(self):
            return [FooType]

        @property
        def tag_mapping(self):
            return []

        @property
        def url_mapping(self):
            return []

    foo = FooType("hello", 42)
    tree = {"foo": foo}

    with pytest.warns(AsdfWarning, match=r"Unable to locate schema file"), asdf.AsdfFile(
        tree,
        extensions=FooExtension(),
    ) as af:
        af.write_to(tmpfile)

    with pytest.warns(AsdfWarning, match=r"Unable to locate schema file"), asdf.AsdfFile(
        tree,
        extensions=FooExtension(),
    ) as ff:
        assert isinstance(ff.tree["foo"], FooType)
        assert ff.tree["foo"] == tree["foo"]


def test_custom_reference_cycle(tmp_path):
    f1 = FractionWithInverse(3, 5)
    f2 = FractionWithInverse(5, 3)
    f1.inverse = f2
    f2.inverse = f1
    tree = {"fraction": f1}

    path = str(tmp_path / "with_inverse.asdf")

    with asdf.AsdfFile(tree, extensions=FractionWithInverseExtension()) as af:
        af.write_to(path)

    with asdf.open(path, extensions=FractionWithInverseExtension()) as af:
        assert af["fraction"].inverse.inverse is af["fraction"]


def test_super_use_in_versioned_subclass():
    """
    Test fix for issue: https://github.com/asdf-format/asdf/issues/1245

    Legacy extensions cannot use super in subclasses of CustomType
    that define supported_versions due to the metaclasses inability
    to create distinct __classcell__ closures.
    """

    class Foo:
        def __init__(self, bar):
            self.bar = bar

    with pytest.raises(RuntimeError, match=r".* ExtensionTypeMeta .* __classcell__ .*"), pytest.warns(
        AsdfDeprecationWarning,
        match=".*subclasses the deprecated CustomType.*",
    ):

        class FooType(asdf.CustomType):
            name = "foo"
            version = (1, 0, 0)
            supported_versions = [(1, 1, 0), (1, 2, 0)]
            types = [Foo]

            @classmethod
            def to_tree(cls, node, ctx):
                return {"bar": node.bar}

            @classmethod
            def from_tree(cls, tree, ctx):
                return Foo(tree["bar"])

            def __getattribute__(self, name):
                return super().__getattribute__(name)
