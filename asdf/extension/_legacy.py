import abc
import warnings
from functools import lru_cache

from asdf import _resolver as resolver
from asdf import _types as types
from asdf._type_index import AsdfTypeIndex
from asdf.exceptions import AsdfDeprecationWarning

__all__ = ["AsdfExtension"]


class AsdfExtension(metaclass=abc.ABCMeta):
    """
    Abstract base class defining a (legacy) extension to ASDF.
    New code should use `asdf.extension.Extension` instead.
    """

    @classmethod
    def __subclasshook__(cls, class_):
        if cls is AsdfExtension:
            return hasattr(class_, "types") and hasattr(class_, "tag_mapping")
        return NotImplemented

    @property
    @abc.abstractmethod
    def types(self):
        """
        A list of `asdf.CustomType` subclasses that describe how to store
        custom objects to and from ASDF.
        """

    @property
    @abc.abstractmethod
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

    @property
    @abc.abstractmethod
    def url_mapping(self):
        """
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


class AsdfExtensionList:
    """
    Manage a set of extensions that are in effect.
    """

    def __init__(self, extensions):
        from ._extension import ExtensionProxy

        extensions = [ExtensionProxy.maybe_wrap(e) for e in extensions]

        tag_mapping = []
        url_mapping = []
        validators = {}
        self._type_index = AsdfTypeIndex()
        for extension in extensions:
            tag_mapping.extend(extension.tag_mapping)
            url_mapping.extend(extension.url_mapping)
            for typ in extension.types:
                self._type_index.add_type(typ, extension)
                validators.update(typ.validators)
                for sibling in typ.versioned_siblings:
                    self._type_index.add_type(sibling, extension)
                    validators.update(sibling.validators)
        self._extensions = extensions
        self._tag_mapping = resolver.Resolver(tag_mapping, "tag")
        self._url_mapping = resolver.Resolver(url_mapping, "url")
        self._resolver = resolver.ResolverChain(self._tag_mapping, self._url_mapping)
        self._validators = validators

    @property
    def tag_to_schema_resolver(self):
        """Deprecated. Use `tag_mapping` instead"""
        warnings.warn(
            "The 'tag_to_schema_resolver' property is deprecated. Use 'tag_mapping' instead.",
            AsdfDeprecationWarning,
        )
        return self._tag_mapping

    @property
    def extensions(self):
        return self._extensions

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


def get_cached_asdf_extension_list(extensions):
    """
    Get a previously created AsdfExtensionList for the specified
    extensions, or create and cache one if necessary.  Building
    the type index is expensive, so it helps performance to reuse
    the index when possible.

    Parameters
    ----------
    extensions : list of asdf.extension.AsdfExtension

    Returns
    -------
    asdf.extension.AsdfExtensionList
    """
    from ._extension import ExtensionProxy

    # The tuple makes the extensions hashable so that we
    # can pass them to the lru_cache method.  The ExtensionProxy
    # overrides __hash__ to return the hashed object id of the wrapped
    # extension, so this will method will only return the same
    # AsdfExtensionList if the list contains identical extension
    # instances in identical order.
    extensions = tuple(ExtensionProxy.maybe_wrap(e) for e in extensions)

    return _get_cached_asdf_extension_list(extensions)


@lru_cache
def _get_cached_asdf_extension_list(extensions):
    return AsdfExtensionList(extensions)


# A kludge in asdf.util.get_class_name allows this class to retain
# its original name, despite being moved from extension.py to
# this file.
class BuiltinExtension:
    """
    This is the "extension" to ASDF that includes all the built-in
    tags.  Even though it's not really an extension and it's always
    available, it's built in the same way as an extension.
    """

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
    @property
    def extensions(self):
        from asdf.config import get_config

        return [e for e in get_config().extensions if e.legacy]

    @property
    def extension_list(self):
        return get_cached_asdf_extension_list(self.extensions)

    @property
    def package_metadata(self):
        return {
            e.class_name: (e.package_name, e.package_version) for e in self.extensions if e.package_name is not None
        }

    def reset(self):
        """This will be used primarily for testing purposes."""
        from asdf.config import get_config

        get_config().reset_extensions()

    @property
    def resolver(self):
        return self.extension_list.resolver


default_extensions = _DefaultExtensions()


def get_default_resolver():
    """
    Get the resolver that includes mappings from all installed extensions.
    """
    return default_extensions.resolver
