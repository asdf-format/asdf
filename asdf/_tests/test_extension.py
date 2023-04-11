import pytest
from packaging.specifiers import SpecifierSet

from asdf import AsdfFile, config_context
from asdf._tests._helpers import assert_extension_correctness
from asdf._types import CustomType
from asdf.exceptions import AsdfDeprecationWarning, ValidationError
from asdf.extension import (
    Compressor,
    Converter,
    ConverterProxy,
    Extension,
    ExtensionManager,
    ExtensionProxy,
    ManifestExtension,
    TagDefinition,
    Validator,
    get_cached_asdf_extension_list,
    get_cached_extension_manager,
)
from asdf.extension._legacy import AsdfExtension, BuiltinExtension


def test_builtin_extension():
    extension = BuiltinExtension()
    with pytest.warns(AsdfDeprecationWarning, match="assert_extension_correctness is deprecated.*"):
        assert_extension_correctness(extension)


with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

    class LegacyType(dict, CustomType):
        organization = "somewhere.org"
        name = "test"
        version = "1.0.0"


class LegacyExtension:
    types = [LegacyType]
    tag_mapping = [("tag:somewhere.org/", "http://somewhere.org/{tag_suffix}")]
    url_mapping = [("http://somewhere.org/", "http://somewhere.org/{url_suffix}.yaml")]


class MinimumExtension:
    extension_uri = "asdf://somewhere.org/extensions/minimum-1.0"


class MinimumExtensionSubclassed(Extension):
    extension_uri = "asdf://somewhere.org/extensions/minimum-1.0"


class FullExtension:
    extension_uri = "asdf://somewhere.org/extensions/full-1.0"

    def __init__(
        self,
        converters=None,
        compressors=None,
        validators=None,
        asdf_standard_requirement=None,
        tags=None,
        legacy_class_names=None,
    ):
        self._converters = [] if converters is None else converters
        self._compressors = [] if compressors is None else compressors
        self._validators = [] if validators is None else validators
        self._asdf_standard_requirement = asdf_standard_requirement
        self._tags = [] if tags is None else tags
        self._legacy_class_names = [] if legacy_class_names is None else legacy_class_names

    @property
    def converters(self):
        return self._converters

    @property
    def compressors(self):
        return self._compressors

    @property
    def validators(self):
        return self._validators

    @property
    def asdf_standard_requirement(self):
        return self._asdf_standard_requirement

    @property
    def tags(self):
        return self._tags

    @property
    def legacy_class_names(self):
        return self._legacy_class_names


class MinimumConverter:
    def __init__(self, tags=None, types=None):
        if tags is None:
            self._tags = []
        else:
            self._tags = tags

        if types is None:
            self._types = []
        else:
            self._types = types

    @property
    def tags(self):
        return self._tags

    @property
    def types(self):
        return self._types

    def to_yaml_tree(self, obj, tag, ctx):
        return "to_yaml_tree result"

    def from_yaml_tree(self, obj, tag, ctx):
        return "from_yaml_tree result"


class FullConverter(MinimumConverter):
    def select_tag(self, obj, tags, ctx):
        return "select_tag result"


class MinimalCompressor(Compressor):
    @staticmethod
    def compress(data):
        return b""

    @property
    def label(self):
        return b"mini"


class MinimalValidator(Validator):
    schema_property = "fail"
    tags = ["**"]

    def validate(self, fail, node, schema):
        if fail:
            yield ValidationError("Node was doomed to fail")


# Some dummy types for testing converters:
class FooType:
    pass


class BarType:
    pass


class BazType:
    pass


def test_extension_proxy_maybe_wrap():
    extension = MinimumExtension()
    proxy = ExtensionProxy.maybe_wrap(extension)
    assert proxy.delegate is extension
    assert ExtensionProxy.maybe_wrap(proxy) is proxy

    with pytest.raises(TypeError, match=r"Extension must implement the Extension or AsdfExtension interface"):
        ExtensionProxy.maybe_wrap(object())


def test_extension_proxy():
    # Test with minimum properties:
    extension = MinimumExtension()
    proxy = ExtensionProxy(extension)

    assert isinstance(proxy, Extension)
    assert isinstance(proxy, AsdfExtension)

    assert proxy.extension_uri == "asdf://somewhere.org/extensions/minimum-1.0"
    assert proxy.legacy_class_names == set()
    assert proxy.asdf_standard_requirement == SpecifierSet()
    assert proxy.converters == []
    assert proxy.compressors == []
    assert proxy.validators == []
    assert proxy.tags == []
    assert proxy.types == []
    assert proxy.tag_mapping == []
    assert proxy.url_mapping == []
    assert proxy.delegate is extension
    assert proxy.legacy is False
    assert proxy.package_name is None
    assert proxy.package_version is None
    assert proxy.class_name == "asdf._tests.test_extension.MinimumExtension"

    # The subclassed version should have the same defaults:
    extension = MinimumExtensionSubclassed()
    subclassed_proxy = ExtensionProxy(extension)
    assert subclassed_proxy.extension_uri == proxy.extension_uri
    assert subclassed_proxy.legacy_class_names == proxy.legacy_class_names
    assert subclassed_proxy.asdf_standard_requirement == proxy.asdf_standard_requirement
    assert subclassed_proxy.converters == proxy.converters
    assert subclassed_proxy.compressors == proxy.compressors
    assert subclassed_proxy.validators == proxy.validators
    assert subclassed_proxy.tags == proxy.tags
    assert subclassed_proxy.types == proxy.types
    assert subclassed_proxy.tag_mapping == proxy.tag_mapping
    assert subclassed_proxy.url_mapping == proxy.url_mapping
    assert subclassed_proxy.delegate is extension
    assert subclassed_proxy.legacy == proxy.legacy
    assert subclassed_proxy.package_name == proxy.package_name
    assert subclassed_proxy.package_version == proxy.package_name
    assert subclassed_proxy.class_name == "asdf._tests.test_extension.MinimumExtensionSubclassed"

    # Test with all properties present:
    converters = [MinimumConverter(tags=["asdf://somewhere.org/extensions/full/tags/foo-*"], types=[])]
    compressors = [MinimalCompressor()]
    validators = [MinimalValidator()]
    extension = FullExtension(
        converters=converters,
        compressors=compressors,
        validators=validators,
        asdf_standard_requirement=">=1.4.0",
        tags=["asdf://somewhere.org/extensions/full/tags/foo-1.0"],
        legacy_class_names=["foo.extensions.SomeOldExtensionClass"],
    )
    proxy = ExtensionProxy(extension, package_name="foo", package_version="1.2.3")

    assert proxy.extension_uri == "asdf://somewhere.org/extensions/full-1.0"
    assert proxy.legacy_class_names == {"foo.extensions.SomeOldExtensionClass"}
    assert proxy.asdf_standard_requirement == SpecifierSet(">=1.4.0")
    assert proxy.converters == [ConverterProxy(c, proxy) for c in converters]
    assert proxy.compressors == compressors
    assert proxy.validators == validators
    assert len(proxy.tags) == 1
    assert proxy.tags[0].tag_uri == "asdf://somewhere.org/extensions/full/tags/foo-1.0"
    assert proxy.types == []
    assert proxy.tag_mapping == []
    assert proxy.url_mapping == []
    assert proxy.delegate is extension
    assert proxy.legacy is False
    assert proxy.package_name == "foo"
    assert proxy.package_version == "1.2.3"
    assert proxy.class_name == "asdf._tests.test_extension.FullExtension"

    # Should fail when the input is not one of the two extension interfaces:
    with pytest.raises(TypeError, match=r"Extension must implement the Extension or AsdfExtension interface"):
        ExtensionProxy(object)

    # Should fail with a bad converter:
    with pytest.raises(TypeError, match=r"Converter must implement the .* interface"):
        ExtensionProxy(FullExtension(converters=[object()]))

    # Should fail with a bad compressor:
    with pytest.raises(TypeError, match=r"Extension property 'compressors' must contain instances of .*"):
        ExtensionProxy(FullExtension(compressors=[object()]))

    # Should fail with a bad validator
    with pytest.raises(TypeError, match=r"Extension property 'validators' must contain instances of .*"):
        ExtensionProxy(FullExtension(validators=[object()]))

    # Unparsable ASDF Standard requirement:
    with pytest.raises(ValueError, match=r"Invalid specifier:.*"):
        ExtensionProxy(FullExtension(asdf_standard_requirement="asdf-standard >= 1.4.0"))

    # Unrecognized ASDF Standard requirement type:
    with pytest.raises(TypeError, match=r"Extension property 'asdf_standard_requirement' must be str or None"):
        ExtensionProxy(FullExtension(asdf_standard_requirement=object()))

    # Bad tag:
    with pytest.raises(TypeError, match=r"Extension property 'tags' must contain str or .* values"):
        ExtensionProxy(FullExtension(tags=[object()]))

    # Bad legacy class names:
    with pytest.raises(TypeError, match=r"Extension property 'legacy_class_names' must contain str values"):
        ExtensionProxy(FullExtension(legacy_class_names=[object]))


def test_extension_proxy_tags():
    """
    The tags behavior is a tad complex, so they get their own test.
    """
    foo_tag_uri = "asdf://somewhere.org/extensions/full/tags/foo-1.0"
    foo_tag_def = TagDefinition(
        foo_tag_uri,
        schema_uris="asdf://somewhere.org/extensions/full/schemas/foo-1.0",
        title="Some tag title",
        description="Some tag description",
    )

    bar_tag_uri = "asdf://somewhere.org/extensions/full/tags/bar-1.0"
    bar_tag_def = TagDefinition(
        bar_tag_uri,
        schema_uris="asdf://somewhere.org/extensions/full/schemas/bar-1.0",
        title="Some other tag title",
        description="Some other tag description",
    )

    # The converter should return only the tags
    # supported by the extension.
    converter = FullConverter(tags=["**"])
    extension = FullExtension(tags=[foo_tag_def], converters=[converter])
    proxy = ExtensionProxy(extension)
    assert proxy.converters[0].tags == [foo_tag_uri]

    # The converter should not return tags that
    # its patterns do not match.
    converter = FullConverter(tags=["**/foo-1.0"])
    extension = FullExtension(tags=[foo_tag_def, bar_tag_def], converters=[converter])
    proxy = ExtensionProxy(extension)
    assert proxy.converters[0].tags == [foo_tag_uri]

    # The process should still work if the extension property
    # contains str instead of TagDescription.
    converter = FullConverter(tags=["**/foo-1.0"])
    extension = FullExtension(tags=[foo_tag_uri, bar_tag_uri], converters=[converter])
    proxy = ExtensionProxy(extension)
    assert proxy.converters[0].tags == [foo_tag_uri]


def test_extension_proxy_legacy():
    extension = LegacyExtension()
    proxy = ExtensionProxy(extension, package_name="foo", package_version="1.2.3")

    assert proxy.extension_uri is None
    assert proxy.legacy_class_names == {"asdf._tests.test_extension.LegacyExtension"}
    assert proxy.asdf_standard_requirement == SpecifierSet()
    assert proxy.converters == []
    assert proxy.tags == []
    assert proxy.types == [LegacyType]
    assert proxy.tag_mapping == LegacyExtension.tag_mapping
    assert proxy.url_mapping == LegacyExtension.url_mapping
    assert proxy.delegate is extension
    assert proxy.legacy is True
    assert proxy.package_name == "foo"
    assert proxy.package_version == "1.2.3"
    assert proxy.class_name == "asdf._tests.test_extension.LegacyExtension"


def test_extension_proxy_hash_and_eq():
    extension = MinimumExtension()
    proxy1 = ExtensionProxy(extension)
    proxy2 = ExtensionProxy(extension, package_name="foo", package_version="1.2.3")

    assert proxy1 == proxy2
    assert hash(proxy1) == hash(proxy2)
    assert proxy1 != extension
    assert proxy2 != extension


def test_extension_proxy_repr():
    proxy = ExtensionProxy(MinimumExtension(), package_name="foo", package_version="1.2.3")
    assert "class: asdf._tests.test_extension.MinimumExtension" in repr(proxy)
    assert "package: foo==1.2.3" in repr(proxy)
    assert "legacy: False" in repr(proxy)

    proxy = ExtensionProxy(MinimumExtension())
    assert "class: asdf._tests.test_extension.MinimumExtension" in repr(proxy)
    assert "package: (none)" in repr(proxy)
    assert "legacy: False" in repr(proxy)

    proxy = ExtensionProxy(LegacyExtension(), package_name="foo", package_version="1.2.3")
    assert "class: asdf._tests.test_extension.LegacyExtension" in repr(proxy)
    assert "package: foo==1.2.3" in repr(proxy)
    assert "legacy: True" in repr(proxy)


def test_extension_manager():
    converter1 = FullConverter(
        tags=[
            "asdf://somewhere.org/extensions/full/tags/foo-*",
            "asdf://somewhere.org/extensions/full/tags/bar-*",
        ],
        types=[
            FooType,
            "asdf._tests.test_extension.BarType",
        ],
    )
    converter2 = FullConverter(
        tags=[
            "asdf://somewhere.org/extensions/full/tags/baz-*",
        ],
        types=[BazType],
    )
    converter3 = FullConverter(
        tags=[
            "asdf://somewhere.org/extensions/full/tags/foo-*",
        ],
        types=[
            FooType,
            BarType,
        ],
    )
    extension1 = FullExtension(
        converters=[converter1, converter2],
        tags=[
            "asdf://somewhere.org/extensions/full/tags/foo-1.0",
            "asdf://somewhere.org/extensions/full/tags/baz-1.0",
        ],
    )
    extension2 = FullExtension(
        converters=[converter3],
        tags=[
            "asdf://somewhere.org/extensions/full/tags/foo-1.0",
        ],
    )

    manager = ExtensionManager([extension1, extension2])

    assert manager.extensions == [ExtensionProxy(extension1), ExtensionProxy(extension2)]

    assert manager.handles_tag("asdf://somewhere.org/extensions/full/tags/foo-1.0") is True
    assert manager.handles_tag("asdf://somewhere.org/extensions/full/tags/bar-1.0") is False
    assert manager.handles_tag("asdf://somewhere.org/extensions/full/tags/baz-1.0") is True

    assert manager.handles_type(FooType) is True
    # This should return True even though BarType was listed
    # as string class name:
    assert manager.handles_type(BarType) is True
    assert manager.handles_type(BazType) is True

    assert (
        manager.get_tag_definition("asdf://somewhere.org/extensions/full/tags/foo-1.0").tag_uri
        == "asdf://somewhere.org/extensions/full/tags/foo-1.0"
    )
    assert (
        manager.get_tag_definition("asdf://somewhere.org/extensions/full/tags/baz-1.0").tag_uri
        == "asdf://somewhere.org/extensions/full/tags/baz-1.0"
    )
    with pytest.raises(KeyError, match=r"No support available for YAML tag.*"):
        manager.get_tag_definition("asdf://somewhere.org/extensions/full/tags/bar-1.0")

    assert manager.get_converter_for_tag("asdf://somewhere.org/extensions/full/tags/foo-1.0").delegate is converter1
    assert manager.get_converter_for_tag("asdf://somewhere.org/extensions/full/tags/baz-1.0").delegate is converter2
    with pytest.raises(KeyError, match=r"No support available for YAML tag.*"):
        manager.get_converter_for_tag("asdf://somewhere.org/extensions/full/tags/bar-1.0")

    assert manager.get_converter_for_type(FooType).delegate is converter1
    assert manager.get_converter_for_type(BarType).delegate is converter1
    assert manager.get_converter_for_type(BazType).delegate is converter2
    with pytest.raises(KeyError, match=r"\"No support available for Python type .*\""):
        manager.get_converter_for_type(object)


def test_get_cached_extension_manager():
    extension = MinimumExtension()
    extension_manager = get_cached_extension_manager([extension])
    assert get_cached_extension_manager([extension]) is extension_manager
    assert get_cached_extension_manager([MinimumExtension()]) is not extension_manager


def test_tag_definition():
    tag_def = TagDefinition(
        "asdf://somewhere.org/extensions/foo/tags/foo-1.0",
        schema_uris="asdf://somewhere.org/extensions/foo/schemas/foo-1.0",
        title="Some title",
        description="Some description",
    )

    assert tag_def.tag_uri == "asdf://somewhere.org/extensions/foo/tags/foo-1.0"
    assert tag_def.schema_uris == ["asdf://somewhere.org/extensions/foo/schemas/foo-1.0"]
    assert tag_def.title == "Some title"
    assert tag_def.description == "Some description"

    assert "URI: asdf://somewhere.org/extensions/foo/tags/foo-1.0" in repr(tag_def)

    with pytest.warns(AsdfDeprecationWarning, match=r"The .* property is deprecated.*"):
        assert tag_def.schema_uri == "asdf://somewhere.org/extensions/foo/schemas/foo-1.0"

    tag_def = TagDefinition(
        "asdf://somewhere.org/extensions/foo/tags/foo-1.0",
        schema_uris=[
            "asdf://somewhere.org/extensions/foo/schemas/foo-1.0",
            "asdf://somewhere.org/extensions/foo/schemas/base-1.0",
        ],
        title="Some title",
        description="Some description",
    )

    assert tag_def.schema_uris == [
        "asdf://somewhere.org/extensions/foo/schemas/foo-1.0",
        "asdf://somewhere.org/extensions/foo/schemas/base-1.0",
    ]
    with pytest.warns(AsdfDeprecationWarning, match=r"The .* property is deprecated.*"), pytest.raises(
        RuntimeError,
        match=r"Cannot use .* when multiple schema URIs are present",
    ):
        tag_def.schema_uri

    with pytest.raises(ValueError, match=r"URI patterns are not permitted in TagDefinition"):
        TagDefinition("asdf://somewhere.org/extensions/foo/tags/foo-*")


def test_converter():
    class ConverterNoSubclass:
        tags = []
        types = []

        def to_yaml_tree(self, *args):
            pass

        def from_yaml_tree(self, *args):
            pass

    assert issubclass(ConverterNoSubclass, Converter)

    class ConverterWithSubclass(Converter):
        tags = []
        types = []

        def to_yaml_tree(self, *args):
            pass

        def from_yaml_tree(self, *args):
            pass

    # Confirm the behavior of the default select_tag implementation
    assert ConverterWithSubclass().select_tag(object(), ["tag1", "tag2"], object()) == "tag1"


def test_converter_proxy():
    # Test the minimum set of converter methods:
    extension = ExtensionProxy(MinimumExtension())
    converter = MinimumConverter()
    proxy = ConverterProxy(converter, extension)

    assert isinstance(proxy, Converter)

    assert proxy.tags == []
    assert proxy.types == []
    assert proxy.to_yaml_tree(None, None, None) == "to_yaml_tree result"
    assert proxy.from_yaml_tree(None, None, None) == "from_yaml_tree result"
    assert proxy.tags == []
    assert proxy.delegate is converter
    assert proxy.extension == extension
    assert proxy.package_name is None
    assert proxy.package_version is None
    assert proxy.class_name == "asdf._tests.test_extension.MinimumConverter"

    # Check the __eq__ and __hash__ behavior:
    assert proxy == ConverterProxy(converter, extension)
    assert proxy != ConverterProxy(MinimumConverter(), extension)
    assert proxy != ConverterProxy(converter, MinimumExtension())
    assert proxy in {ConverterProxy(converter, extension)}
    assert proxy not in {ConverterProxy(MinimumConverter(), extension), ConverterProxy(converter, MinimumExtension())}

    # Check the __repr__:
    assert "class: asdf._tests.test_extension.MinimumConverter" in repr(proxy)
    assert "package: (none)" in repr(proxy)

    # Test the full set of converter methods:
    converter = FullConverter(
        tags=[
            "asdf://somewhere.org/extensions/test/tags/foo-*",
            "asdf://somewhere.org/extensions/test/tags/bar-*",
        ],
        types=[FooType, BarType],
    )

    extension = FullExtension(
        tags=[
            TagDefinition(
                "asdf://somewhere.org/extensions/test/tags/foo-1.0",
                schema_uris="asdf://somewhere.org/extensions/test/schemas/foo-1.0",
                title="Foo tag title",
                description="Foo tag description",
            ),
            TagDefinition(
                "asdf://somewhere.org/extensions/test/tags/bar-1.0",
                schema_uris="asdf://somewhere.org/extensions/test/schemas/bar-1.0",
                title="Bar tag title",
                description="Bar tag description",
            ),
        ],
    )

    extension_proxy = ExtensionProxy(extension, package_name="foo", package_version="1.2.3")
    proxy = ConverterProxy(converter, extension_proxy)
    assert len(proxy.tags) == 2
    assert "asdf://somewhere.org/extensions/test/tags/foo-1.0" in proxy.tags
    assert "asdf://somewhere.org/extensions/test/tags/bar-1.0" in proxy.tags
    assert proxy.types == [FooType, BarType]
    assert proxy.to_yaml_tree(None, None, None) == "to_yaml_tree result"
    assert proxy.from_yaml_tree(None, None, None) == "from_yaml_tree result"
    assert proxy.select_tag(None, None) == "select_tag result"
    assert proxy.delegate is converter
    assert proxy.extension == extension_proxy
    assert proxy.package_name == "foo"
    assert proxy.package_version == "1.2.3"
    assert proxy.class_name == "asdf._tests.test_extension.FullConverter"

    # Check the __repr__ since it will contain package info now:
    assert "class: asdf._tests.test_extension.FullConverter" in repr(proxy)
    assert "package: foo==1.2.3" in repr(proxy)

    # Should error because object() does fulfill the Converter interface:
    with pytest.raises(TypeError, match=r"Converter must implement the .*"):
        ConverterProxy(object(), extension)

    # Should fail because tags must be str:
    with pytest.raises(TypeError, match=r"Converter property .* must contain str values"):
        ConverterProxy(MinimumConverter(tags=[object()]), extension)

    # Should fail because types must instances of type:
    with pytest.raises(TypeError, match=r"Converter property .* must contain str or type values"):
        ConverterProxy(MinimumConverter(types=[object()]), extension)


def test_get_cached_asdf_extension_list():
    extension = LegacyExtension()
    with pytest.warns(AsdfDeprecationWarning, match="get_cached_asdf_extension_list is deprecated"):
        extension_list = get_cached_asdf_extension_list([extension])
    with pytest.warns(AsdfDeprecationWarning, match="get_cached_asdf_extension_list is deprecated"):
        assert get_cached_asdf_extension_list([extension]) is extension_list
    with pytest.warns(AsdfDeprecationWarning, match="get_cached_asdf_extension_list is deprecated"):
        assert get_cached_asdf_extension_list([LegacyExtension()]) is not extension_list


def test_manifest_extension():
    with config_context() as config:
        minimal_manifest = """%YAML 1.1
---
id: asdf://somewhere.org/manifests/foo
extension_uri: asdf://somewhere.org/extensions/foo
...
"""
        config.add_resource_mapping({"asdf://somewhere.org/extensions/foo": minimal_manifest})
        extension = ManifestExtension.from_uri("asdf://somewhere.org/extensions/foo")
        assert isinstance(extension, Extension)
        assert extension.extension_uri == "asdf://somewhere.org/extensions/foo"
        assert extension.legacy_class_names == []
        assert extension.asdf_standard_requirement is None
        assert extension.converters == []
        assert extension.compressors == []
        assert extension.validators == []
        assert extension.tags == []

        proxy = ExtensionProxy(extension)
        assert proxy.extension_uri == "asdf://somewhere.org/extensions/foo"
        assert proxy.legacy_class_names == set()
        assert proxy.asdf_standard_requirement == SpecifierSet()
        assert proxy.converters == []
        assert proxy.compressors == []
        assert proxy.validators == []
        assert proxy.tags == []

    with config_context() as config:
        full_manifest = """%YAML 1.1
---
id: asdf://somewhere.org/manifests/foo
extension_uri: asdf://somewhere.org/extensions/foo
asdf_standard_requirement:
  gte: 1.6.0
  lt: 2.0.0
tags:
  - asdf://somewhere.org/tags/bar
  - tag_uri: asdf://somewhere.org/tags/baz
    schema_uri: asdf://somewhere.org/schemas/baz
    title: Baz title
    description: Bar description
...
"""
        config.add_resource_mapping({"asdf://somewhere.org/extensions/foo": full_manifest})

        class FooConverter:
            tags = ["asdf://somewhere.org/tags/bar", "asdf://somewhere.org/tags/baz"]
            types = []

            def select_tag(self, *args):
                pass

            def to_yaml_tree(self, *args):
                pass

            def from_yaml_tree(self, *args):
                pass

        converter = FooConverter()
        validator = MinimalValidator()
        compressor = MinimalCompressor()

        extension = ManifestExtension.from_uri(
            "asdf://somewhere.org/extensions/foo",
            legacy_class_names=["foo.extension.LegacyExtension"],
            converters=[converter],
            compressors=[compressor],
            validators=[validator],
        )
        assert extension.extension_uri == "asdf://somewhere.org/extensions/foo"
        assert extension.legacy_class_names == ["foo.extension.LegacyExtension"]
        assert extension.asdf_standard_requirement == SpecifierSet(">=1.6.0,<2.0.0")
        assert extension.converters == [converter]
        assert extension.compressors == [compressor]
        assert extension.validators == [validator]
        assert len(extension.tags) == 2
        assert extension.tags[0] == "asdf://somewhere.org/tags/bar"
        assert extension.tags[1].tag_uri == "asdf://somewhere.org/tags/baz"
        assert extension.tags[1].schema_uris == ["asdf://somewhere.org/schemas/baz"]
        assert extension.tags[1].title == "Baz title"
        assert extension.tags[1].description == "Bar description"

        proxy = ExtensionProxy(extension)
        assert proxy.extension_uri == "asdf://somewhere.org/extensions/foo"
        assert proxy.legacy_class_names == {"foo.extension.LegacyExtension"}
        assert proxy.asdf_standard_requirement == SpecifierSet(">=1.6.0,<2.0.0")
        assert proxy.converters == [ConverterProxy(converter, proxy)]
        assert proxy.compressors == [compressor]
        assert proxy.validators == [validator]
        assert len(proxy.tags) == 2
        assert proxy.tags[0].tag_uri == "asdf://somewhere.org/tags/bar"
        assert proxy.tags[1].tag_uri == "asdf://somewhere.org/tags/baz"
        assert proxy.tags[1].schema_uris == ["asdf://somewhere.org/schemas/baz"]
        assert proxy.tags[1].title == "Baz title"
        assert proxy.tags[1].description == "Bar description"

    with config_context() as config:
        simple_asdf_standard_manifest = """%YAML 1.1
---
id: asdf://somewhere.org/manifests/foo
extension_uri: asdf://somewhere.org/extensions/foo
asdf_standard_requirement: 1.6.0
...
"""
        config.add_resource_mapping({"asdf://somewhere.org/extensions/foo": simple_asdf_standard_manifest})
        extension = ManifestExtension.from_uri("asdf://somewhere.org/extensions/foo")
        assert extension.asdf_standard_requirement == SpecifierSet("==1.6.0")

        proxy = ExtensionProxy(extension)
        assert proxy.asdf_standard_requirement == SpecifierSet("==1.6.0")


def test_validator():
    validator = MinimalValidator()
    extension = FullExtension(validators=[validator])

    failing_schema = """
        type: object
        properties:
          foo:
            fail: true
    """

    passing_schema = """
        type: object
        properties:
          foo:
            fail: false
    """

    with config_context() as config:
        config.add_extension(extension)
        config.add_resource_mapping(
            {
                "asdf://somewhere.org/schemas/failing": failing_schema,
                "asdf://somewhere.org/schemas/passing": passing_schema,
            },
        )

        with AsdfFile(custom_schema="asdf://somewhere.org/schemas/passing") as af:
            af["foo"] = "bar"
            af.validate()

        with AsdfFile(custom_schema="asdf://somewhere.org/schemas/failing") as af:
            af.validate()

            af["foo"] = "bar"
            with pytest.raises(ValidationError, match=r"Node was doomed to fail"):
                af.validate()
