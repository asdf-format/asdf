"""
Support for Converter, the new API for serializing custom
types.  Will eventually replace the `asdf.types` module.
"""

import abc

from asdf.util import get_class_name, uri_match


class Converter(abc.ABC):
    """
    Abstract base class for plugins that convert nodes from the
    parsed YAML tree into custom objects, and vice versa.

    Implementing classes must provide the `tags` and `types`
    properties and `to_yaml_tree` and `from_yaml_tree` methods.
    The ``select_tag`` method is optional.

    If implemented, ``select_tag`` should accept 3 parameters

        obj : object
            Instance of the custom type being converted.  Guaranteed
            to be an instance of one of the types listed in the
            `types` property.
        tags : list of str
            List of active tags to choose from.  Guaranteed to match
            one of the tag patterns listed in the 'tags' property.
        ctx : asdf.extension.SerializationContext
            Context of the current serialization request.

    and return a str, the selected tag (should be one of tags) or
    `None` which will trigger the result of ``to_yaml_tree`` to be
    used to look up the next converter for this object.

    The ``lazy`` attribute is optional. If ``True`` asdf will
    pass "lazy" objects to the converter. If ``False`` (or not
    defined) asdf will convert all child objects before calling
    `from_yaml_tree`.

    The ``to_info`` method is optional. If implemented it must
    accept 1 parameter ``obj` which is a tree node/custom
    object and return a container (list, tuple, dict) containing
    information about that object to display during ``AsdfFile.info``.
    """

    @classmethod
    def __subclasshook__(cls, class_):
        if cls is Converter:
            return (
                hasattr(class_, "tags")
                and hasattr(class_, "types")
                and hasattr(class_, "to_yaml_tree")
                and hasattr(class_, "from_yaml_tree")
            )
        return NotImplemented  # pragma: no cover

    @property
    @abc.abstractmethod
    def tags(self):
        """
        Get the YAML tags that this converter is capable of
        handling.  URI patterns are permitted, see
        `asdf.util.uri_match` for details.

        Returns
        -------
        iterable of str
            Tag URIs or URI patterns.
        """

    @property
    @abc.abstractmethod
    def types(self):
        """
        Get the Python types that this converter is capable of
        handling.

        Returns
        -------
        iterable of str or type
            If str, the fully qualified class name of the type.
        """

    @abc.abstractmethod
    def to_yaml_tree(self, obj, tag, ctx):
        """
        Convert an object into a node suitable for YAML serialization.
        This method is not responsible for writing actual YAML; rather, it
        converts an instance of a custom type to a built-in Python object type
        (such as dict, list, str, or number), which can then be automatically
        serialized to YAML as needed.

        For container types returned by this method (dict or list),
        the children of the container need not themselves be converted.
        Any list elements or dict values will be converted by subsequent
        calls to to_yaml_tree implementations.

        The returned node must be an instance of `dict`, `list`, or `str`.
        Children may be any type supported by an available Converter.

        Parameters
        ----------
        obj : object
            Instance of a custom type to be serialized.  Guaranteed to
            be an instance of one of the types listed in the `types`
            property.
        tag : str
            The tag identifying the YAML type that ``obj`` should be
            converted into.  Selected by a call to this converter's
            select_tag method.
        ctx : asdf.extension.SerializationContext
            The context of the current serialization request.

        Returns
        -------
        dict or list or str
            The YAML node representation of the object.
        """

    @abc.abstractmethod
    def from_yaml_tree(self, node, tag, ctx):
        """
        Convert a YAML node into an instance of a custom type.

        For container types received by this method (dict or list),
        the children of the container will have already been converted
        by prior calls to from_yaml_tree implementations unless
        ``lazy_tree`` was set to ``True`` for `asdf.open`. With a lazy
        tree the container types will be `asdf.lazy_nodes` (which act
        like dict or list but convert child objects when accessed).

        Note on circular references: trees that reference themselves
        among their descendants must be handled with care.  Most
        implementations need not concern themselves with this case, but
        if the custom type supports circular references, then the
        implementation of this method will need to return a generator.
        Consult the documentation for more details.

        Parameters
        ----------
        node : dict or list or str
            The YAML node to convert.
        tag : str
            The YAML tag of the object being converted.
        ctx : asdf.extension.SerializationContext
            The context of the current deserialization request.

        Returns
        -------
        object
            An instance of one of the types listed in the `types` property,
            or a generator that yields such an instance.
        """


class ConverterProxy(Converter):
    """
    Proxy that wraps a `Converter` and provides default
    implementations of optional methods.
    """

    def __init__(self, delegate, extension):
        if not isinstance(delegate, Converter):
            msg = "Converter must implement the asdf.extension.Converter interface"
            raise TypeError(msg)

        self._delegate = delegate
        self._extension = extension
        self._class_name = get_class_name(delegate)

        # Sort these out up-front so that errors are raised when the extension is loaded
        # and not in the middle of the user's session.  The extension will fail to load
        # and a warning will be emitted, but it won't crash the program.

        relevant_tags = set()
        for tag in delegate.tags:
            if isinstance(tag, str):
                relevant_tags.update(t.tag_uri for t in extension.tags if uri_match(tag, t.tag_uri))
            else:
                msg = "Converter property 'tags' must contain str values"
                raise TypeError(msg)

        if len(relevant_tags) > 1 and not hasattr(delegate, "select_tag"):
            msg = "Converter handles multiple tags for this extension, but does not implement a select_tag method."
            raise RuntimeError(msg)

        self._tags = sorted(relevant_tags)

        self._types = []

        if not len(self._tags) and not hasattr(delegate, "select_tag"):
            # this converter supports no tags so don't inspect the types
            return

        for typ in delegate.types:
            if isinstance(typ, (str, type)):
                self._types.append(typ)
            else:
                msg = "Converter property 'types' must contain str or type values"
                raise TypeError(msg)

    @property
    def lazy(self):
        """
        Boolean indicating if this Converter supports "lazy" node objects

        Returns
        -------
        bool
        """
        return getattr(self._delegate, "lazy", False)

    @property
    def tags(self):
        """
        Get the list of tag URIs that this converter is capable of
        handling.

        Returns
        -------
        list of str
        """
        return self._tags

    @property
    def types(self):
        """
        Get the Python types that this converter is capable of
        handling.

        Returns
        -------
        list of type or str
        """
        return self._types

    def select_tag(self, obj, ctx):
        """
        Select the tag to use when converting an object to YAML.

        Parameters
        ----------
        obj : object
            Instance of the custom type being converted.
        ctx : asdf.extension.SerializationContext
            Serialization parameters.

        Returns
        -------
        str or None
            Selected tag or `None` to defer conversion.
        """
        method = getattr(self._delegate, "select_tag", None)
        if method is None:
            return self._tags[0]

        return method(obj, self._tags, ctx)

    def to_yaml_tree(self, obj, tag, ctx):
        """
        Convert an object into a node suitable for YAML serialization.

        Parameters
        ----------
        obj : object
            Instance of a custom type to be serialized.
        tag : str
            The tag identifying the YAML type that ``obj`` should be
            converted into.
        ctx : asdf.extension.SerializationContext
            Serialization parameters.

        Returns
        -------
        object
            The YAML node representation of the object.
        """
        return self._delegate.to_yaml_tree(obj, tag, ctx)

    def from_yaml_tree(self, node, tag, ctx):
        """
        Convert a YAML node into an instance of a custom type.

        Parameters
        ----------
        tree : dict or list or str
            The YAML node to convert.
        tag : str
            The YAML tag of the object being converted.
        ctx : asdf.extension.SerializationContext
            Serialization parameters.

        Returns
        -------
        object
        """
        return self._delegate.from_yaml_tree(node, tag, ctx)

    def to_info(self, obj):
        """
        Convert an object to a container with items further
        defining information about this node. This method
        is used for "info" and not used for serialization.

        Parameters
        ----------
        obj : object
            Instance of a custom type to get "info" for.

        Returns
        -------
        object
            Must be a container (list, tuple, dict) with
            items providing "info" about ``obj``.
        """
        if not hasattr(self._delegate, "to_info"):
            return obj
        return self._delegate.to_info(obj)

    @property
    def delegate(self):
        """
        Get the wrapped converter instance.

        Returns
        -------
        asdf.extension.Converter
        """
        return self._delegate

    @property
    def extension(self):
        """
        Get the extension that provided this converter.

        Returns
        -------
        asdf.extension.ExtensionProxy
        """
        return self._extension

    @property
    def package_name(self):
        """
        Get the name of the Python package of this converter's
        extension.  This may not be the same package that implements
        the converter's class.

        Returns
        -------
        str or None
            Package name, or `None` if the extension was added at runtime.
        """
        return self.extension.package_name

    @property
    def package_version(self):
        """
        Get the version of the Python package of this converter's
        extension.  This may not be the same package that implements
        the converter's class.

        Returns
        -------
        str or None
            Package version, or `None` if the extension was added at runtime.
        """
        return self.extension.package_version

    @property
    def class_name(self):
        """
        Get the fully qualified class name of this converter.

        Returns
        -------
        str
        """
        return self._class_name

    def __eq__(self, other):
        if isinstance(other, ConverterProxy):
            return other.delegate is self.delegate and other.extension is self.extension

        return False

    def __hash__(self):
        return hash((id(self.delegate), id(self.extension)))

    def __repr__(self):
        package_description = "(none)" if self.package_name is None else f"{self.package_name}=={self.package_version}"

        return f"<ConverterProxy class: {self.class_name} package: {package_description}>"
