import abc
import warnings

from packaging.specifiers import SpecifierSet

from . import types
from . import resolver
from .util import get_class_name
from .type_index import AsdfTypeIndex
from .exceptions import AsdfDeprecationWarning


__all__ = ['AsdfExtension', 'AsdfExtensionList']


class AsdfExtension(abc.ABC):
    """
    Abstract base class defining an extension to ASDF.
    """
    @classmethod
    def __subclasshook__(cls, C):
        if cls is AsdfExtension:
            # At this time, no attributes are required.
            return True
        return NotImplemented # pragma: no cover

    @property
    def default(self):
        """
        Return `True` if this extension should be enabled by default
        for new files (with a supported ASDF Standard version).
        Typically extension packages will designate the latest version
        of an extension as a default.

        Users can reconfigure default extensions globally or on an
        individual file basis. This flag does not enable the extension
        when reading existing files.  Instead, extensions will be
        automatically enabled based on file metadata.

        Returns
        -------
        bool
        """
        return False

    @property
    def always_enabled(self):
        """
        Return `True` if this extension should always be enabled
        when reading and writing files (with a supported ASDF
        Standard version).  When `False`, the extension will only be
        enabled when requested by the user or when listed in a file's
        metadata.

        Users will still be able to remove the extension
        with a call to `AsdfConfig.remove_extension`.

        Defaults to `False` for new-style extensions and `True`
        for legacy extensions.

        Returns
        -------
        bool
        """
        return False

    @property
    def legacy_class_names(self):
        """
        Get the set of fully-qualified class names used by
        older versions of this extension.  This allows a
        new-style implementation of an extension to override
        a legacy extension.

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
        return None

    @property
    def types(self):
        """
        A list of `asdf.CustomType` subclasses that describe how to store
        custom objects to and from ASDF.
        """
        return []

    @property
    def tag_mapping(self):
        """
        A list of 2-tuples or callables mapping YAML tag prefixes to JSON Schema
        URL prefixes.

        For each entry:

        - If a 2-tuple, the first part of the tuple is a YAML tag
          prefix to match.  The second part is a string, where case
          the following are available as Python formatting tokens:

          - ``{tag}``: the complete YAML tag.
          - ``{tag_suffix}``: the part of the YAML tag after the
            matched prefix.
          - ``{tag_prefix}``: the matched YAML tag prefix.

        - If a callable, it is passed the entire YAML tag must return
          the entire JSON schema URL if it matches, otherwise, return `None`.

        Note that while JSON Schema URLs uniquely define a JSON
        Schema, they do not have to actually exist on an HTTP server
        and be fetchable (much like XML namespaces).

        For example, to match all YAML tags with the
        ``tag:nowhere.org:custom` prefix to the
        ``http://nowhere.org/schemas/custom/`` URL prefix::

           return [('tag:nowhere.org:custom/',
                    'http://nowhere.org/schemas/custom/{tag_suffix}')]
        """
        return []

    @property
    def url_mapping(self):
        """
        DEPRECATED.  This property will be ignored in asdf 3.0.
        Schema content can be provided using the resource Mapping API.

        A list of 2-tuples or callables mapping JSON Schema URLs to
        other URLs.  This is useful if the JSON Schemas are not
        actually fetchable at their corresponding URLs but are on the
        local filesystem, or, to save bandwidth, we have a copy of
        fetchable schemas on the local filesystem.  If neither is
        desirable, it may simply be the empty list.

        For each entry:

        - If a 2-tuple, the first part is a URL prefix to match.  The
          second part is a string, where the following are available
          as Python formatting tokens:

          - ``{url}``: The entire JSON schema URL
          - ``{url_prefix}``: The matched URL prefix
          - ``{url_suffix}``: The part of the URL after the prefix.

        - If a callable, it is passed the entire JSON Schema URL and
          must return a resolvable URL pointing to the schema content.
          If it doesn't match, should return `None`.

        For example, to map a remote HTTP URL prefix to files installed
        alongside as data alongside Python module::

            return [('http://nowhere.org/schemas/custom/1.0.0/',
                    asdf.util.filepath_to_url(
                        os.path.join(SCHEMA_PATH, 'stsci.edu')) +
                    '/{url_suffix}.yaml'
                   )]
        """
        return []


class ExtensionProxy(AsdfExtension):
    """
    Proxy that wraps an `AsdfExtension`, provides default
    implementations of optional methods, and carries additional
    information on the package that provided the extension.
    """
    @classmethod
    def maybe_wrap(self, delegate):
        if isinstance(delegate, ExtensionProxy):
            return delegate
        else:
            return ExtensionProxy(delegate)

    def __init__(self, delegate, package_name=None, package_version=None, legacy=False):
        if not isinstance(delegate, AsdfExtension):
            raise TypeError("Extension must implement the AsdfExtension interface")

        self._delegate = delegate
        self._package_name = package_name
        self._package_version = package_version
        self._legacy = legacy

        self._class_name = get_class_name(delegate)

        self._asdf_standard_requirement = None

    @property
    def default(self):
        return getattr(self._delegate, "default", False)

    @property
    def always_enabled(self):
        return getattr(self._delegate, "always_enabled", False)

    @property
    def legacy_class_names(self):
        return set(getattr(self._delegate, "legacy_class_names", set()))

    @property
    def asdf_standard_requirement(self):
        if self._asdf_standard_requirement is None:
            value = getattr(self._delegate, "asdf_standard_requirement", None)
            if isinstance(value, str):
                self._asdf_standard_requirement = SpecifierSet(value)
            elif value is None:
                self._asdf_standard_requirement = SpecifierSet()
            else:
                raise TypeError("asdf_standard_requirement must be str or None")
        return self._asdf_standard_requirement

    @property
    def types(self):
        return getattr(self._delegate, "types", [])

    @property
    def tag_mapping(self):
        return getattr(self._delegate, "tag_mapping", [])

    @property
    def url_mapping(self):
        return getattr(self._delegate, "url_mapping", [])

    @property
    def delegate(self):
        return self._delegate

    @property
    def class_name(self):
        return self._class_name

    @property
    def package_name(self):
        return self._package_name

    @property
    def package_version(self):
        return self._package_version

    @property
    def legacy(self):
        return self._legacy

    def __repr__(self):
        if self.package_name is None:
            package_description = "(none)"
        else:
            package_description = "{}=={}".format(self.package_name, self.package_version)

        requirement_description = str(self.asdf_standard_requirement)
        if requirement_description == "":
            requirement_description = "(all)"

        return "<ExtensionProxy class: {} package: {} ASDF Standard: {} legacy: {}>".format(
            self.class_name,
            package_description,
            requirement_description,
            self.legacy,
        )


class AsdfExtensionList:
    """
    Manage a set of extensions that are in effect.
    """
    def __init__(self, extensions):
        self._extensions = [ExtensionProxy.maybe_wrap(e) for e in extensions]
        tag_mapping = []
        url_mapping = []
        validators = {}
        self._type_index = AsdfTypeIndex()
        for extension in self._extensions:
            if not isinstance(extension, AsdfExtension):
                raise TypeError(
                    "Extension must implement asdf.types.AsdfExtension "
                    "interface")
            tag_mapping.extend(extension.tag_mapping)
            url_mapping.extend(extension.url_mapping)
            for typ in extension.types:
                self._type_index.add_type(typ, extension)
                validators.update(typ.validators)
                for sibling in typ.versioned_siblings:
                    self._type_index.add_type(sibling, extension)
                    validators.update(sibling.validators)
        self._tag_mapping = resolver.Resolver(tag_mapping, 'tag')
        self._url_mapping = resolver.Resolver(url_mapping, 'url')
        self._resolver = resolver.ResolverChain(self._tag_mapping, self._url_mapping)
        self._validators = validators

    @property
    def extensions(self):
        return self._extensions

    @property
    def tag_to_schema_resolver(self):
        """Deprecated. Use `tag_mapping` instead"""
        warnings.warn(
            "The 'tag_to_schema_resolver' property is deprecated. Use "
            "'tag_mapping' instead.",
            AsdfDeprecationWarning)
        return self._tag_mapping

    @property
    def tag_mapping(self):
        return self._tag_mapping

    @property
    def url_mapping(self):
        return self._url_mapping

    @property
    def resolver(self):
        return self._resolver

    @property
    def type_index(self):
        return self._type_index

    @property
    def validators(self):
        return self._validators


class BuiltinExtension:
    """
    This is the "extension" to ASDF that includes all the built-in
    tags.  Even though it's not really an extension and it's always
    available, it's built in the same way as an extension.
    """
    always_enabled = True

    @property
    def types(self):
        return types._all_asdftypes

    @property
    def tag_mapping(self):
        return resolver.DEFAULT_TAG_TO_URL_MAPPING

    @property
    def url_mapping(self):
        return resolver.DEFAULT_URL_MAPPING


class _DefaultExtensions:
    def __init__(self):
        self._extensions = None
        self._extension_list = None

    @property
    def extensions(self):
        if self._extensions is None:
            from ._config import get_config
            self._extensions = [e for e in get_config().extensions if e.legacy]
        return self._extensions

    @property
    def extension_list(self):
        if self._extension_list is None:
            self._extension_list = AsdfExtensionList(self.extensions)
        return self._extension_list

    def reset(self):
        """This will be used primarily for testing purposes."""
        self._extensions = None
        self._extension_list = None

    @property
    def resolver(self):
        return self.extension_list.resolver


default_extensions = _DefaultExtensions()


def get_default_resolver():
    """
    Get the resolver that includes mappings from all installed extensions.
    """
    return default_extensions.resolver
