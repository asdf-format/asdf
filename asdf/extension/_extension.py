import abc

from packaging.specifiers import SpecifierSet

from asdf.util import get_class_name

from ._compressor import Compressor
from ._converter import ConverterProxy
from ._tag import TagDefinition
from ._validator import Validator


class Extension(abc.ABC):
    """
    Abstract base class defining an extension to ASDF.

    Implementing classes must provide the `extension_uri`.
    Other properties are optional.
    """

    @classmethod
    def __subclasshook__(cls, class_):
        if cls is Extension:
            return hasattr(class_, "extension_uri")
        return NotImplemented  # pragma: no cover

    @property
    @abc.abstractmethod
    def extension_uri(self):
        """
        Get the URI of the extension to the ASDF Standard implemented
        by this class.  Note that this may not uniquely identify the
        class itself.

        Returns
        -------
        str
        """

    @property
    def legacy_class_names(self):
        """
        Get the set of fully-qualified class names used by older
        versions of this extension.  This allows a new-style
        implementation of an extension to prevent warnings when a
        legacy extension is missing.

        Returns
        -------
        iterable of str
        """
        return set()

    @property
    def asdf_standard_requirement(self):
        """
        Get the ASDF Standard version requirement for this extension.

        Returns
        -------
        str or None
            If str, PEP 440 version specifier.
            If None, support all versions.
        """
        return

    @property
    def converters(self):
        """
        Get the `asdf.extension.Converter` instances for tags
        and Python types supported by this extension.

        Returns
        -------
        iterable of asdf.extension.Converter
        """
        return []

    @property
    def tags(self):
        """
        Get the YAML tags supported by this extension.

        Returns
        -------
        iterable of str or asdf.extension.TagDefinition
        """
        return []

    @property
    def compressors(self):
        """
        Get the `asdf.extension.Compressor` instances for
        compression schemes supported by this extension.

        Returns
        -------
        iterable of asdf.extension.Compressor
        """
        return []

    @property
    def yaml_tag_handles(self):
        """
        Get a dictionary of custom yaml TAG handles defined by the extension.

        The dictionary key indicates the TAG handles to be placed in the YAML header,
        the value defines the string for tag replacement.
        See https://yaml.org/spec/1.1/#tag%20shorthand/

        Example: ``{"!foo!": "tag:nowhere.org:custom/"}``

        Returns
        -------
        dict

        """
        return {}

    @property
    def validators(self):
        """
        Get the `asdf.extension.Validator` instances for additional
        schema properties supported by this extension.

        Returns
        -------
        iterable of asdf.extension.Validator
        """
        return []


class ExtensionProxy(Extension):
    """
    Proxy that wraps an extension, provides default implementations
    of optional methods, and carries additional information on the
    package that provided the extension.
    """

    @classmethod
    def maybe_wrap(cls, delegate):
        if isinstance(delegate, ExtensionProxy):
            return delegate

        return ExtensionProxy(delegate)

    def __init__(self, delegate, package_name=None, package_version=None):
        if not isinstance(delegate, Extension):
            msg = "Extension must implement the Extension interface"
            raise TypeError(msg)

        self._delegate = delegate
        self._package_name = package_name
        self._package_version = package_version

        self._class_name = get_class_name(delegate)

        self._legacy = False

        # Sort these out up-front so that errors are raised when the extension is loaded
        # and not in the middle of the user's session.  The extension will fail to load
        # and a warning will be emitted, but it won't crash the program.

        self._legacy_class_names = set()
        for class_name in getattr(self._delegate, "legacy_class_names", []):
            if isinstance(class_name, str):
                self._legacy_class_names.add(class_name)
            else:
                msg = "Extension property 'legacy_class_names' must contain str values"
                raise TypeError(msg)

        if self._legacy:
            self._legacy_class_names.add(self._class_name)

        value = getattr(self._delegate, "asdf_standard_requirement", None)
        if isinstance(value, str):
            self._asdf_standard_requirement = SpecifierSet(value)
        elif value is None:
            self._asdf_standard_requirement = SpecifierSet()
        else:
            msg = "Extension property 'asdf_standard_requirement' must be str or None"
            raise TypeError(msg)

        self._tags = []
        for tag in getattr(self._delegate, "tags", []):
            if isinstance(tag, str):
                self._tags.append(TagDefinition(tag))
            elif isinstance(tag, TagDefinition):
                self._tags.append(tag)
            else:
                msg = "Extension property 'tags' must contain str or asdf.extension.TagDefinition values"
                raise TypeError(msg)

        self._yaml_tag_handles = getattr(delegate, "yaml_tag_handles", {})

        # Process the converters last, since they expect ExtensionProxy
        # properties to already be available.
        self._converters = [ConverterProxy(c, self) for c in getattr(self._delegate, "converters", [])]

        self._compressors = []
        if hasattr(self._delegate, "compressors"):
            for compressor in self._delegate.compressors:
                if not isinstance(compressor, Compressor):
                    msg = "Extension property 'compressors' must contain instances of asdf.extension.Compressor"
                    raise TypeError(msg)
                self._compressors.append(compressor)

        self._validators = []
        if hasattr(self._delegate, "validators"):
            for validator in self._delegate.validators:
                if not isinstance(validator, Validator):
                    msg = "Extension property 'validators' must contain instances of asdf.extension.Validator"
                    raise TypeError(msg)
                self._validators.append(validator)

    @property
    def extension_uri(self):
        """
        Get the URI of the extension to the ASDF Standard implemented
        by this class.  Note that this may not uniquely identify the
        class itself.

        Returns
        -------
        str or None
        """
        return getattr(self._delegate, "extension_uri", None)

    @property
    def legacy_class_names(self):
        """
        Get the set of fully-qualified class names used by older
        versions of this extension.  This allows a new-style
        implementation of an extension to prevent warnings when a
        legacy extension is missing.

        Returns
        -------
        set of str
        """
        return self._legacy_class_names

    @property
    def asdf_standard_requirement(self):
        """
        Get the extension's ASDF Standard requirement.

        Returns
        -------
        packaging.specifiers.SpecifierSet
        """
        return self._asdf_standard_requirement

    @property
    def converters(self):
        """
        Get the extension's converters.

        Returns
        -------
        list of asdf.extension.Converter
        """
        return self._converters

    @property
    def compressors(self):
        """
        Get the extension's compressors.

        Returns
        -------
        list of asdf.extension.Compressor
        """
        return self._compressors

    @property
    def tags(self):
        """
        Get the YAML tags supported by this extension.

        Returns
        -------
        list of asdf.extension.TagDefinition
        """
        return self._tags

    @property
    def types(self):
        """
        Get the legacy extension's ExtensionType subclasses.

        Returns
        -------
        iterable of asdf.type.ExtensionType
        """
        return getattr(self._delegate, "types", [])

    @property
    def tag_mapping(self):
        """
        Get the legacy extension's tag-to-schema-URI mapping.

        Returns
        -------
        iterable of tuple or callable
        """
        return getattr(self._delegate, "tag_mapping", [])

    @property
    def url_mapping(self):
        """
        Get the legacy extension's schema-URI-to-URL mapping.

        Returns
        -------
        iterable of tuple or callable
        """
        return getattr(self._delegate, "url_mapping", [])

    @property
    def delegate(self):
        """
        Get the wrapped extension instance.

        Returns
        -------
        asdf.extension.Extension
        """
        return self._delegate

    @property
    def package_name(self):
        """
        Get the name of the Python package that provided this extension.

        Returns
        -------
        str or None
            `None` if the extension was added at runtime.
        """
        return self._package_name

    @property
    def package_version(self):
        """
        Get the version of the Python package that provided the extension

        Returns
        -------
        str or None
            `None` if the extension was added at runtime.
        """
        return self._package_version

    @property
    def class_name(self):
        """
        Get the fully qualified class name of the extension.

        Returns
        -------
        str
        """
        return self._class_name

    @property
    def legacy(self):
        """
        False
        """
        return self._legacy

    @property
    def yaml_tag_handles(self):
        """
        Get a dictionary of custom yaml TAG handles defined by the extension.

        The dictionary key indicates the TAG handles to be placed in the YAML header,
        the value defines the string for tag replacement.
        See https://yaml.org/spec/1.1/#tag%20shorthand/

        Example: ``{"!foo!": "tag:nowhere.org:custom/"}``

        Returns
        -------
        dict

        """
        return self._yaml_tag_handles

    @property
    def validators(self):
        """
        Get the `asdf.extension.Validator` instances for additional
        schema properties supported by this extension.

        Returns
        -------
        list of asdf.extension.Validator
        """
        return self._validators

    def __eq__(self, other):
        if isinstance(other, ExtensionProxy):
            return other.delegate is self.delegate

        return False

    def __hash__(self):
        return hash(id(self.delegate))

    def __repr__(self):
        package_description = "(none)" if self.package_name is None else f"{self.package_name}=={self.package_version}"

        uri_description = "(none)" if self.extension_uri is None else self.extension_uri

        return (
            f"<ExtensionProxy URI: {uri_description} class: {self.class_name} "
            f"package: {package_description} legacy: {self.legacy}>"
        )
