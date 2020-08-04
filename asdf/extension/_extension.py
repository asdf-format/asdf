from ..util import get_class_name
from ._legacy import AsdfExtension


class ExtensionProxy(AsdfExtension):
    """
    Proxy that wraps an extension, provides default implementations
    of optional methods, and carries additional information on the
    package that provided the extension.
    """
    @classmethod
    def maybe_wrap(self, delegate):
        if isinstance(delegate, ExtensionProxy):
            return delegate
        else:
            return ExtensionProxy(delegate)

    def __init__(self, delegate, package_name=None, package_version=None):
        if not isinstance(delegate, AsdfExtension):
            raise TypeError("Extension must implement the AsdfExtension interface")

        self._delegate = delegate
        self._package_name = package_name
        self._package_version = package_version

        self._class_name = get_class_name(delegate)

        self._legacy = True

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
        asdf.extension.AsdfExtension
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
        Get the extension's legacy flag.  Subclasses of `asdf.extension.AsdfExtension`
        are marked `True`.

        Returns
        -------
        bool
        """
        return self._legacy

    def __eq__(self, other):
        if isinstance(other, ExtensionProxy):
            return other.delegate is self.delegate
        else:
            return False

    def __hash__(self):
        return hash(id(self.delegate))

    def __repr__(self):
        if self.package_name is None:
            package_description = "(none)"
        else:
            package_description = "{}=={}".format(self.package_name, self.package_version)

        return "<ExtensionProxy class: {} package: {} legacy: {}>".format(
            self.class_name,
            package_description,
            self.legacy,
        )
