import collections
import fractions
import sys

import pytest
from packaging.specifiers import SpecifierSet

import asdf
from asdf import AsdfFile, config_context
from asdf.exceptions import AsdfManifestURIMismatchWarning, AsdfSerializationError, ValidationError
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
    get_cached_extension_manager,
)
from asdf.extension._manager import _resolve_type
from asdf.testing.helpers import roundtrip_object


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


class SubFooType(FooType):
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

    with pytest.raises(TypeError, match=r"Extension must implement the Extension interface"):
        ExtensionProxy.maybe_wrap(object())


def test_extension_proxy():
    # Test with minimum properties:
    extension = MinimumExtension()
    proxy = ExtensionProxy(extension)

    assert isinstance(proxy, Extension)

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
    with pytest.raises(TypeError, match=r"Extension must implement the Extension interface"):
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
    assert manager.handles_type(SubFooType) is False
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
    with pytest.raises(KeyError, match=r"\"No support available for Python type .*\""):
        manager.get_converter_for_type(SubFooType)


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
        # as the code will ignore types if no relevant tags are found
        # include a tag from this extension to make sure the proxy considers
        # the types
        ConverterProxy(MinimumConverter(tags=[extension.tags[0].tag_uri], types=[object()]), extension)


def test_converter_subclass_with_no_supported_tags():
    """
    Adding a Converter to an Extension that doesn't list support for the tags
    associated with the Converter should result in a failure to convert.
    """

    class Foo:
        pass

    class FooConverterWithSubclass(Converter):
        tags = ["asdf://somewhere.org/tags/foo-1.0.0"]
        types = [Foo]

        def to_yaml_tree(self, *args):
            pass

        def from_yaml_tree(self, *args):
            pass

    class FooExtension(Extension):
        tags = []
        converters = [FooConverterWithSubclass()]
        extension_uri = "asdf://somewhere.org/extensions/foo-1.0.0"

    tree = {"obj": Foo()}
    with config_context() as cfg:
        cfg.add_extension(FooExtension())
        with pytest.raises(AsdfSerializationError, match=r"is not serializable by asdf"):
            roundtrip_object(tree)


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


def test_converter_deferral():
    class Bar:
        def __init__(self, value):
            self.value = value

    class Foo(Bar):
        pass

    class Baz(Bar):
        pass

    class FooConverter:
        tags = []
        types = [Foo]

        def select_tag(self, *args):
            return None

        def to_yaml_tree(self, obj, tag, ctx):
            # convert Foo instance to Bar
            return Bar(obj.value)

        def from_yaml_tree(self, node, tag, ctx):
            raise NotImplementedError()

    class BarConverter:
        tags = ["asdf://somewhere.org/tags/bar"]
        types = [Bar]

        def to_yaml_tree(self, obj, tag, ctx):
            return {"value": obj.value}

        def from_yaml_tree(self, node, tag, ctx):
            return Bar(node["value"])

    class BazConverter:
        tags = []
        types = [Baz]

        def select_tag(self, *args):
            return None

        def to_yaml_tree(self, obj, tag, ctx):
            return Foo(obj.value)

        def from_yaml_tree(self, node, tag, ctx):
            raise NotImplementedError()

    extension = FullExtension(converters=[FooConverter(), BarConverter(), BazConverter()], tags=BarConverter.tags)
    with config_context() as config:
        config.add_extension(extension)

        foo = Foo(26)
        bar = Bar(42)
        baz = Baz(720)

        bar_rt = roundtrip_object(bar)
        assert isinstance(bar_rt, Bar)
        assert bar_rt.value == bar.value

        foo_rt = roundtrip_object(foo)
        assert isinstance(foo_rt, Bar)
        assert foo_rt.value == foo.value

        baz_rt = roundtrip_object(baz)
        assert isinstance(baz_rt, Bar)
        assert baz_rt.value == baz.value


def test_converter_loop():
    class Bar:
        def __init__(self, value):
            self.value = value

    class Foo(Bar):
        pass

    class Baz(Bar):
        pass

    class FooConverter:
        tags = []
        types = [Foo]

        def select_tag(self, *args):
            return None

        def to_yaml_tree(self, obj, tag, ctx):
            return Bar(obj.value)

        def from_yaml_tree(self, node, tag, ctx):
            raise NotImplementedError()

    class BarConverter:
        tags = []
        types = [Bar]

        def select_tag(self, *args):
            return None

        def to_yaml_tree(self, obj, tag, ctx):
            return Baz(obj.value)

        def from_yaml_tree(self, node, tag, ctx):
            raise NotImplementedError()

    class BazConverter:
        tags = []
        types = [Baz]

        def select_tag(self, *args):
            return None

        def to_yaml_tree(self, obj, tag, ctx):
            return Foo(obj.value)

        def from_yaml_tree(self, node, tag, ctx):
            raise NotImplementedError()

    extension = FullExtension(converters=[FooConverter(), BarConverter(), BazConverter()])
    with config_context() as config:
        config.add_extension(extension)

        for typ in (Foo, Bar, Baz):
            obj = typ(42)
            with pytest.raises(TypeError, match=r"Conversion cycle detected"):
                roundtrip_object(obj)


@pytest.mark.parametrize("is_subclass", [True, False])
@pytest.mark.parametrize("indirect", [True, False])
def test_warning_or_error_for_default_select_tag(is_subclass, indirect):
    class Foo:
        pass

    ParentClass = Converter if is_subclass else object

    if indirect:

        class IntermediateClass(ParentClass):
            pass

        ParentClass = IntermediateClass

    class FooConverter(ParentClass):
        tags = ["asdf://somewhere.org/tags/foo-*"]
        types = [Foo]

        def to_yaml_tree(self, obj, tag, ctx):
            return {}

        def from_yaml_tree(self, node, tag, ctx):
            return Foo()

    tags = [
        "asdf://somewhere.org/tags/foo-1.0.0",
        "asdf://somewhere.org/tags/foo-2.0.0",
    ]
    extension = FullExtension(converters=[FooConverter()], tags=tags)
    with config_context() as config:
        with pytest.raises(RuntimeError, match="Converter handles multiple tags"):
            config.add_extension(extension)


def test_reference_cycle(tmp_path, with_lazy_tree):
    class FractionWithInverse(fractions.Fraction):
        def __init__(self, *args, **kwargs):
            self._inverse = None

        @property
        def inverse(self):
            return self._inverse

        @inverse.setter
        def inverse(self, value):
            self._inverse = value

    class FractionWithInverseConverter:
        tags = ["asdf://example.com/fractions/tags/fraction-1.0.0"]
        types = [FractionWithInverse]

        def to_yaml_tree(self, obj, tag, ctx):
            return {
                "numerator": obj.numerator,
                "denominator": obj.denominator,
                "inverse": obj.inverse,
            }

        def from_yaml_tree(self, node, tag, ctx):
            obj = FractionWithInverse(node["numerator"], node["denominator"])
            yield obj
            obj.inverse = node["inverse"]

    class FractionWithInverseExtension:
        tags = FractionWithInverseConverter.tags
        converters = [FractionWithInverseConverter()]
        extension_uri = "asdf://example.com/fractions/extensions/fraction-1.0.0"

    with config_context() as cfg:
        cfg.add_extension(FractionWithInverseExtension())

        f1 = FractionWithInverse(3, 5)
        f2 = FractionWithInverse(5, 3)
        f1.inverse = f2
        f2.inverse = f1
        fn = tmp_path / "test.asdf"
        asdf.AsdfFile({"obj": f1}).write_to(fn)
        with asdf.open(fn) as af:
            read_f1 = af["obj"]
            assert read_f1.inverse.inverse is read_f1


def test_manifest_uri_id_mismatch_warning(tmp_path):
    with config_context() as config:
        # make an extension with a manifest (where id doesn't match the registered uri)
        full_manifest = """%YAML 1.1
---
id: asdf://somewhere.org/manifests/foo
extension_uri: asdf://somewhere.org/extensions/foo
tags:
  - asdf://somewhere.org/tags/bar
...
"""
        config.add_resource_mapping({"asdf://somewhere.org/extensions/foo": full_manifest})

        class Foo:
            pass

        class FooConverter:
            tags = ["asdf://somewhere.org/tags/bar"]
            types = [Foo]

            def to_yaml_tree(self, *args):
                return {}

            def from_yaml_tree(self, *args):
                return Foo()

        extension = ManifestExtension.from_uri(
            "asdf://somewhere.org/extensions/foo",
            converters=[FooConverter()],
        )

        # use the extension to write out a file
        config.add_extension(extension)

        af = AsdfFile()
        af["foo"] = Foo()
        fn = tmp_path / "foo.asdf"
        with pytest.warns(AsdfManifestURIMismatchWarning):
            af.write_to(fn)


def test_resolve_type_not_imported():
    path = "mailbox.Mailbox"

    if "mailbox" in sys.modules:
        del sys.modules["mailbox"]

    assert _resolve_type(path) is None

    import mailbox

    assert _resolve_type(path) is mailbox.Mailbox


@pytest.mark.parametrize(
    "path, obj", (("sys", sys), ("asdf.AsdfFile", AsdfFile), ("asdf.Missing", None), ("not_a_module", None))
)
def test_resolve_type(path, obj):
    assert _resolve_type(path) is obj


def test_extension_converter_by_class_path():
    class MailboxConverter:
        tags = ["asdf://example.com/tags/mailbox-1.0.0"]
        types = ["mailbox.Mailbox"]

        def to_yaml_tree(self, obj, tag, ctx):
            return {}

        def from_yaml_tree(self, node, tag, ctx):
            return None

    class MailboxExtension:
        tags = MailboxConverter.tags
        converters = [MailboxConverter()]
        extension_uri = "asdf://example.com/extensions/mailbox-1.0.0"

    # grab the type so we can use it for extension_manager.get_converter_for_type
    import mailbox

    typ = mailbox.Mailbox
    del sys.modules["mailbox"], mailbox

    with config_context() as cfg:
        cfg.add_extension(MailboxExtension())
        extension_manager = AsdfFile().extension_manager

        # make sure that registering the extension did not load the module
        assert "mailbox" not in sys.modules

        # as the module hasn't been loaded, the converter shouldn't be found
        with pytest.raises(KeyError, match="No support available for Python type 'mailbox.Mailbox'"):
            extension_manager.get_converter_for_type(typ)

        # make sure inspecting the type didn't import the module
        assert "mailbox" not in sys.modules

        # finally, import the module and check that the converter can now be found
        import mailbox

        converter = extension_manager.get_converter_for_type(mailbox.Mailbox)
        assert isinstance(converter.delegate, MailboxConverter)


def test_named_tuple_extension():
    Point = collections.namedtuple("Point", ["x", "y"])

    class PointConverter:
        tags = ["asdf://example.com/tags/point-1.0.0"]
        types = [Point]

        def to_yaml_tree(self, obj, tag, ctx):
            return list(obj)

        def from_yaml_tree(self, node, tag, ctx):
            return Point(*node)

    class PointExtension:
        tags = PointConverter.tags
        converters = [PointConverter()]
        extension_uri = "asdf://example.com/extensions/point-1.0.0"

    pt = Point(1, 2)

    # without the extension we can't serialize this
    with pytest.raises(AsdfSerializationError, match="is not serializable by asdf"):
        roundtrip_object(pt)

    with config_context() as cfg:
        cfg.add_extension(PointExtension())
        rpt = roundtrip_object(pt)
        assert isinstance(rpt, Point)
