"""
Support for AsdfConverter, the new API for constructing custom
objects.  Will eventually replace the `asdf.types` and
`asdf.type_index` modules.
"""
from pkg_resources import parse_version


class AsdfConverterMeta(type):
    """
    Metaclass that provides validation of the AsdfConverter
    class attributes.
    """
    def __new__(mcls, name, bases, attrs):
        if "tags" in attrs:
            tags = attrs["tags"]
            if not isinstance(tags, set) or not all(isinstance(t, str) for t in tags):
                raise TypeError("{} 'tags' attribute must be a set of string values".format(name))

        if "types" in attrs:
            types = attrs["types"]
            if not isinstance(types, set) or not all(isinstance(t, type) for t in types):
                raise TypeError("{} 'types' attribute must be a set of type instances".format(name))

        return super().__new__(mcls, name, bases, attrs)


class AsdfConverter(metaclass=AsdfConverterMeta):
    """
    Base class for built-in and user-defined classes that convert
    nodes from the parsed YAML tree into custom objects, and vice versa.

    Subclasses must set the `tags` and `types` class attributes
    and define implementations of the `to_yaml_tree` and
    `from_yaml_tree` instance methods.

    Note that the API of this class does not permit manipulation of
    the AsdfFile's binary blocks.

    Parameters
    ----------
    tag : str
        The single tag that is handled by this AsdfConverter instance.

    Attributes
    ----------
    tags : set of str
        Set of URI values used to tag objects in YAML.

    types : set of type
        Set of custom types converted by this class.
    """
    tags = set()
    types = set()

    @classmethod
    def create_converters(cls):
        """
        Create all instances of this class needed to support the tags
        and types specified in the class attributes.

        Returns
        -------
        list of asdf.AsdfConverter
            List of instances, one per tag.
        """
        return [cls(tag) for tag in cls.tags]

    def __init__(self, tag):
        self.tag = tag

    @property
    def version(self):
        """
        Extract the version portion of this converter's tag.

        Returns
        -------
        str
            The version string
        """
        return self.tag.rsplit("-", 1)[-1]

    def to_yaml_tree(self, obj):
        """
        Convert an object into an object tree suitable for YAML serialization.
        This method is not responsible for writing actual YAML; rather, it
        converts an instance of a custom type to a tree of built-in Python types
        (such as dict, list, str, or number), which can then be automatically
        serialized to YAML as needed.

        For container types returned by this method (dict or list),
        the children of the container should not themselves be converted.
        Any list elements or dict values will be converted by subsequent
        calls to to_yaml_tree implementations.

        The root node of the returned tree must be an instance of `dict`,
        `list`, or `str`.  Descendants of the root node may be any
        type supported by YAML serialization.

        Parameters
        ----------
        obj : object
            Instance of a custom type to be serialized.  Guaranteed to
            be an instance of one of the types listed in the `types` class
            attribute.

        Returns
        -------
        dict or list or str
            The tree representation of the object. Implementations that
            wish to override the tag used to identify the object in YAML
            are free to instead return an instance of `asdf.tagged.TaggedDict`,
            `asdf.tagged.TaggedList`, or `asdf.tagged.TaggedString`.
        """
        raise NotImplementedError("AsdfConverter subclasses must implement to_yaml_tree")

    def from_yaml_tree(self, tree):
        """
        Convert a YAML subtree into an instance of a custom type.

        For container types received by this method (dict or list),
        the children of the container will have already been converted
        by prior calls to from_yaml_tree implementations.

        Note on circular references: trees that reference themselves
        among their descendants must be handled with care.  Most
        implementations need not concern themselves with this case, but
        if the custom type supports circular references, then the
        implementation of this method will need to return a generator.
        Consult the documentation for more details.

        Parameters
        ----------
        tree : dict or list or str
            The YAML subtree to convert.  For the sake of performance, this
            object will actually be an instance of `asdf.tagged.TaggedDict`,
            `asdf.tagged.TaggedList`, or `asdf.tagged.TaggedString`.  These
            objects should behave identically to their built-in counterparts.

        Returns
        -------
        object
            An instance of one of the types listed in the `types` class
            attribute, or a generator that yields such an instance.
        """

        raise NotImplementedError("AsdfConverter subclasses must implement from_yaml_tree")


# TODO(eslavich): Implement base class for converters that manipulate blocks


class ConverterCollection:
    def __init__(self, converters):
        self._converters_by_tag = {}
        self._converters_by_type_by_tag = {}

        for converter in converters:
            if converter.tag in self._converters_by_tag:
                other_converter = self._converters_by_tag[converter.tag]
                message = (
                    "AsdfConverter for tag '{}' provided by both {} and {}. "
                    "Please deselect one of the conflicting extensions.".format(
                        converter.tag,
                        type(other_converter.extension).__name__,
                        type(converter.extension).__name__,
                    )
                )
                raise ValueError(message)
            self._converters_by_tag[converter.tag] = converter

            for typ in converter.types:
                if typ not in self._converters_by_type_by_tag:
                    self._converters_by_type_by_tag[typ] = {}

                self._converters_by_type_by_tag[typ][converter.tag] = converter

    def from_tag(self, tag):
        return self._converters_by_tag.get(tag)

    def from_type(self, typ):
        # TODO(eslavich): This needs to be determined by schema collection information,
        # but for now we'll just return the latest.
        return self._select_latest_converter(typ)

    def _select_latest_converter(self, typ):
        converters_by_tag = self._converters_by_type_by_tag.get(typ, {})
        if len(converters_by_tag) == 0:
            return None

        return sorted(list(converters_by_tag.values()), key=lambda c: parse_version(c.version))[-1]
