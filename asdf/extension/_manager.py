from functools import lru_cache

from ..util import get_class_name
from ._extension import ExtensionProxy


class ExtensionManager:
    """
    Wraps a list of extensions and indexes their converters
    by tag and by Python type.

    Parameters
    ----------
    extensions : iterable of asdf.extension.Extension
        List of enabled extensions to manage.  Extensions placed earlier
        in the list take precedence.
    """

    def __init__(self, extensions):
        self._extensions = [ExtensionProxy.maybe_wrap(e) for e in extensions]

        self._tag_defs_by_tag = {}
        self._converters_by_tag = {}
        # This dict has both str and type keys:
        self._converters_by_type = {}

        for extension in self._extensions:
            for tag_def in extension.tags:
                if tag_def.tag_uri not in self._tag_defs_by_tag:
                    self._tag_defs_by_tag[tag_def.tag_uri] = tag_def
            for converter in extension.converters:
                # If a converter's tags do not actually overlap with
                # the extension tag list, then there's no reason to
                # use it.
                if len(converter.tags) > 0:
                    for tag in converter.tags:
                        if tag not in self._converters_by_tag:
                            self._converters_by_tag[tag] = converter
                    for typ in converter.types:
                        if isinstance(typ, str):
                            if typ not in self._converters_by_type:
                                self._converters_by_type[typ] = converter
                        else:
                            type_class_name = get_class_name(typ, instance=False)
                            if typ not in self._converters_by_type and type_class_name not in self._converters_by_type:
                                self._converters_by_type[typ] = converter
                                self._converters_by_type[type_class_name] = converter

    @property
    def extensions(self):
        """
        Get the list of extensions.

        Returns
        -------
        list of asdf.extension.ExtensionProxy
        """
        return self._extensions

    def handles_tag(self, tag):
        """
        Return `True` if the specified tag is handled by a
        converter.

        Parameters
        ----------
        tag : str
            Tag URI.

        Returns
        -------
        bool
        """
        return tag in self._converters_by_tag

    def handles_type(self, typ):
        """
        Returns `True` if the specified Python type is handled
        by a converter.

        Parameters
        ----------
        typ : type

        Returns
        -------
        bool
        """
        return typ in self._converters_by_type or get_class_name(typ, instance=False) in self._converters_by_type

    def handles_tag_definition(self, tag):
        """
        Return `True` if the specified tag has a definition.

        Parameters
        ----------
        tag : str
            Tag URI.

        Returns
        -------
        bool
        """
        return tag in self._tag_defs_by_tag

    def get_tag_definition(self, tag):
        """
        Get the tag definition for the specified tag.

        Parameters
        ----------
        tag : str
            Tag URI.

        Returns
        -------
        asdf.extension.TagDefinition

        Raises
        ------
        KeyError
            Unrecognized tag URI.
        """
        try:
            return self._tag_defs_by_tag[tag]
        except KeyError:
            raise KeyError(
                "No support available for YAML tag '{}'.  " "You may need to install a missing extension.".format(tag)
            ) from None

    def get_converter_for_tag(self, tag):
        """
        Get the converter for the specified tag.

        Parameters
        ----------
        tag : str
            Tag URI.

        Returns
        -------
        asdf.extension.Converter

        Raises
        ------
        KeyError
            Unrecognized tag URI.
        """
        try:
            return self._converters_by_tag[tag]
        except KeyError:
            raise KeyError(
                "No support available for YAML tag '{}'.  " "You may need to install a missing extension.".format(tag)
            ) from None

    def get_converter_for_type(self, typ):
        """
        Get the converter for the specified Python type.

        Parameters
        ----------
        typ : type

        Returns
        -------
        asdf.extension.Converter

        Raises
        ------
        KeyError
            Unrecognized type.
        """
        try:
            return self._converters_by_type[typ]
        except KeyError:
            class_name = get_class_name(typ, instance=False)
            try:
                return self._converters_by_type[class_name]
            except KeyError:
                raise KeyError(
                    "No support available for Python type '{}'.  "
                    "You may need to install or enable an extension.".format(get_class_name(typ, instance=False))
                ) from None


def get_cached_extension_manager(extensions):
    """
    Get a previously created ExtensionManager for the specified
    extensions, or create and cache one if necessary.  Building
    the manager is expensive, so it helps performance to reuse
    it when possible.

    Parameters
    ----------
    extensions : list of asdf.extension.AsdfExtension or asdf.extension.Extension

    Returns
    -------
    asdf.extension.ExtensionManager
    """
    from ._extension import ExtensionProxy

    # The tuple makes the extensions hashable so that we
    # can pass them to the lru_cache method.  The ExtensionProxy
    # overrides __hash__ to return the hashed object id of the wrapped
    # extension, so this will method will only return the same
    # ExtensionManager if the list contains identical extension
    # instances in identical order.
    extensions = tuple(ExtensionProxy.maybe_wrap(e) for e in extensions)

    return _get_cached_extension_manager(extensions)


@lru_cache
def _get_cached_extension_manager(extensions):
    return ExtensionManager(extensions)
