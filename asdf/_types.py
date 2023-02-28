import importlib
import re
import warnings
from copy import copy

import asdf.testing.helpers

from . import tagged, util
from .exceptions import AsdfDeprecationWarning
from .versioning import AsdfSpec, AsdfVersion

__all__ = ["format_tag", "CustomType", "AsdfType", "ExtensionType"]  # noqa: F822


# regex used to parse module name from optional version string
MODULE_RE = re.compile(r"([a-zA-Z]+)(-(\d+\.\d+\.\d+))?")


def __getattr__(name):
    if name == "format_tag":
        warnings.warn(
            "asdf.types.format_tag is deprecated. Please use asdf.testing.helpers.format_tag",
            AsdfDeprecationWarning,
        )
        return asdf.testing.helpers.format_tag
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


_all_asdftypes = set()


def _from_tree_tagged_missing_requirements(cls, tree, ctx):
    # A special version of AsdfType.from_tree_tagged for when the
    # required dependencies for an AsdfType are missing.
    plural, verb = ("s", "are") if len(cls.requires) else ("", "is")

    # This error will be handled by yamlutil.tagged_tree_to_custom_tree, which
    # will cause a warning to be issued indicating that the tree failed to be
    # converted.
    msg = f"{util.human_list(cls.requires)} package{plural} {verb} required to instantiate '{tree._tag}'"
    raise TypeError(msg)


class ExtensionTypeMeta(type):
    """
    Custom class constructor for tag types.
    """

    _import_cache = {}

    @classmethod
    def _has_required_modules(cls, requires):
        for string in requires:
            has_module = True
            match = MODULE_RE.match(string)
            modname, _, version = match.groups()
            if modname in cls._import_cache and not cls._import_cache[modname]:
                return False

            try:
                module = importlib.import_module(modname)
                if version and hasattr(module, "__version__") and module.__version__ < version:
                    has_module = False

            except ImportError:
                has_module = False

            finally:
                cls._import_cache[modname] = has_module
                if not has_module:
                    return False  # noqa: B012

        return True

    @classmethod
    def _find_in_bases(cls, attrs, bases, name, default=None):
        if name in attrs:
            return attrs[name]
        for base in bases:
            if hasattr(base, name):
                return getattr(base, name)
        return default

    @property
    def versioned_siblings(cls):
        return getattr(cls, "__versioned_siblings") or []

    def __new__(cls, name, bases, attrs):
        requires = cls._find_in_bases(attrs, bases, "requires", [])
        if not cls._has_required_modules(requires):
            attrs["from_tree_tagged"] = classmethod(_from_tree_tagged_missing_requirements)
            attrs["types"] = []
            attrs["has_required_modules"] = False
        else:
            attrs["has_required_modules"] = True
            types = cls._find_in_bases(attrs, bases, "types", [])
            new_types = []
            for type_ in types:
                new_types.append(util.resolve_name(type_) if isinstance(type_, str) else type_)

            attrs["types"] = new_types

        new_cls = super().__new__(cls, name, bases, attrs)

        if hasattr(new_cls, "version") and not isinstance(new_cls.version, (AsdfVersion, AsdfSpec)):
            new_cls.version = AsdfVersion(new_cls.version)

        if hasattr(new_cls, "name"):
            if isinstance(new_cls.name, str):
                if "yaml_tag" not in attrs:
                    new_cls.yaml_tag = new_cls.make_yaml_tag(new_cls.name)
            elif isinstance(new_cls.name, list):
                pass
            elif new_cls.name is not None:
                msg = "name must be string or list"
                raise TypeError(msg)

        if hasattr(new_cls, "supported_versions"):
            if not isinstance(new_cls.supported_versions, (list, set)):
                new_cls.supported_versions = [new_cls.supported_versions]
            supported_versions = set()
            for version in new_cls.supported_versions:
                # This should cause an exception for invalid input
                supported_versions.add(
                    version if isinstance(version, (AsdfVersion, AsdfSpec)) else AsdfVersion(version),
                )
            # We need to convert back to a list here so that the 'in' operator
            # uses actual comparison instead of hash equality
            new_cls.supported_versions = list(supported_versions)
            siblings = []
            for version in new_cls.supported_versions:
                if version != new_cls.version:
                    new_attrs = copy(attrs)
                    new_attrs["version"] = version
                    new_attrs["supported_versions"] = set()
                    new_attrs["_latest_version"] = new_cls.version
                    if "__classcell__" in new_attrs:
                        msg = (
                            "Subclasses of ExtensionTypeMeta that define "
                            "supported_versions cannot used super() to call "
                            "parent class functions. super() creates a "
                            "__classcell__ closure that cannot be duplicated "
                            "during creation of versioned siblings. "
                            "See https://github.com/asdf-format/asdf/issues/1245"
                        )
                        raise RuntimeError(msg)
                    siblings.append(ExtensionTypeMeta.__new__(cls, name, bases, new_attrs))
            setattr(new_cls, "__versioned_siblings", siblings)

        return new_cls


class AsdfTypeMeta(ExtensionTypeMeta):
    """
    Keeps track of `AsdfType` subclasses that are created, and stores them in
    `AsdfTypeIndex`.
    """

    def __new__(cls, name, bases, attrs):
        new_cls = super().__new__(cls, name, bases, attrs)
        # Classes using this metaclass get added to the list of built-in
        # extensions
        if name != "AsdfType":
            _all_asdftypes.add(new_cls)

        return new_cls


class ExtensionType:
    """
    The base class of all custom types in the tree.

    Besides the attributes defined below, most subclasses will also
    override ``to_tree`` and ``from_tree``.
    """

    name = None
    organization = "stsci.edu"
    standard = "asdf"
    version = (1, 0, 0)
    supported_versions = set()
    types = []
    handle_dynamic_subclasses = False
    validators = {}
    requires = []
    yaml_tag = None

    @classmethod
    def names(cls):
        """
        Returns the name(s) represented by this tag type as a list.

        While some tag types represent only a single custom type, others
        represent multiple types. In the latter case, the `name` attribute of
        the extension is actually a list, not simply a string. This method
        normalizes the value of `name` by returning a list in all cases.

        Returns
        -------
            `list` of names represented by this tag type
        """
        if cls.name is None:
            return None

        return cls.name if isinstance(cls.name, list) else [cls.name]

    @classmethod
    def make_yaml_tag(cls, name, versioned=True):
        """
        Given the name of a type, returns a string representing its YAML tag.

        Parameters
        ----------
        name : str
            The name of the type. In most cases this will correspond to the
            `name` attribute of the tag type. However, it is passed as a
            parameter since some tag types represent multiple custom
            types.

        versioned : bool
            If `True`, the tag will be versioned. Otherwise, a YAML tag without
            a version will be returned.

        Returns
        -------
            `str` representing the YAML tag
        """
        return asdf.testing.helpers.format_tag(cls.organization, cls.standard, cls.version if versioned else None, name)

    @classmethod
    def tag_base(cls):
        """
        Returns the base of the YAML tag for types represented by this class.

        This method returns the portion of the tag that represents the standard
        and the organization of any type represented by this class.

        Returns
        -------
            `str` representing the base of the YAML tag
        """
        return cls.make_yaml_tag("", versioned=False)

    @classmethod
    def to_tree(cls, node, ctx):
        """
        Converts instances of custom types into YAML representations.

        This method should be overridden by custom extension classes in order
        to define how custom types are serialized into YAML. The method must
        return a single Python object corresponding to one of the basic YAML
        types (dict, list, str, or number). However, the types can be nested
        and combined in order to represent more complex custom types.

        This method is called as part of the process of writing an `asdf.AsdfFile`
        object. Whenever a custom type (or a subclass of that type) that is
        listed in the `types` attribute of this class is encountered, this
        method will be used to serialize that type.

        The name `to_tree` refers to the act of converting a custom type into
        part of a YAML object tree.

        Parameters
        ----------
        node : `object`
            Instance of a custom type to be serialized. Will be an instance (or
            an instance of a subclass) of one of the types listed in the
            `types` attribute of this class.

        ctx : `asdf.AsdfFile`
            An instance of the `asdf.AsdfFile` object that is being written out.

        Returns
        -------
            A basic YAML type (`dict`, `list`, `str`, `int`, `float`, or
            `complex`) representing the properties of the custom type to be
            serialized. These types can be nested in order to represent more
            complex custom types.
        """
        return node.__class__.__bases__[0](node)

    @classmethod
    def to_tree_tagged(cls, node, ctx):
        """
        Converts instances of custom types into tagged objects.

        It is more common for custom tag types to override `to_tree` instead of
        this method. This method should be overridden if it is necessary
        to modify the YAML tag that will be used to tag this object.

        Parameters
        ----------
        node : `object`
            Instance of a custom type to be serialized. Will be an instance (or
            an instance of a subclass) of one of the types listed in the
            `types` attribute of this class.

        ctx : `asdf.AsdfFile`
            An instance of the `asdf.AsdfFile` object that is being written out.

        Returns
        -------
            An instance of `asdf.tagged.Tagged`.
        """
        obj = cls.to_tree(node, ctx)
        return tagged.tag_object(cls.yaml_tag, obj, ctx=ctx)

    @classmethod
    def from_tree(cls, tree, ctx):
        """
        Converts basic types representing YAML trees into custom types.

        This method should be overridden by custom extension classes in order
        to define how custom types are deserialized from the YAML
        representation back into their original types. Typically the method will
        return an instance of the original custom type.  It is also permitted
        to return a generator, which yields a partially constructed result, then
        completes construction once the generator is drained.  This is useful
        when constructing objects that contain reference cycles.

        This method is called as part of the process of reading an ASDF file in
        order to construct an `asdf.AsdfFile` object. Whenever a YAML subtree is
        encountered that has a tag that corresponds to the `yaml_tag` property
        of this class, this method will be used to deserialize that tree back
        into an instance of the original custom type.

        Parameters
        ----------
        tree : `object` representing YAML tree
            An instance of a basic Python type (possibly nested) that
            corresponds to a YAML subtree.

        ctx : `asdf.AsdfFile`
            An instance of the `asdf.AsdfFile` object that is being constructed.

        Returns
        -------
            An instance of the custom type represented by this extension class,
            or a generator that yields that instance.
        """
        return cls(tree)

    @classmethod
    def from_tree_tagged(cls, tree, ctx):
        """
        Converts from tagged tree into custom type.

        It is more common for extension classes to override `from_tree` instead
        of this method. This method should only be overridden if it is
        necessary to access the `_tag` property of the `~asdf.tagged.Tagged` object
        directly.

        Parameters
        ----------
        tree : `asdf.tagged.Tagged` object representing YAML tree

        ctx : `asdf.AsdfFile`
            An instance of the `asdf.AsdfFile` object that is being constructed.

        Returns
        -------
            An instance of the custom type represented by this extension class.
        """
        return cls.from_tree(tree.data, ctx)

    @classmethod
    def incompatible_version(cls, version):
        """
        Indicates if given version is known to be incompatible with this type.

        If this tag class explicitly identifies compatible versions then this
        checks whether a given version is compatible or not (see
        `supported_versions`). Otherwise, all versions are assumed to be
        compatible.

        Child classes can override this method to affect how version
        compatibility for this type is determined.

        Parameters
        ----------
        version : `str` or `~asdf.versioning.AsdfVersion`
            The version to test for compatibility.
        """
        if cls.supported_versions and version not in cls.supported_versions:
            return True

        return False


class AsdfType(ExtensionType, metaclass=AsdfTypeMeta):
    """
    Base class for all built-in ASDF types. Types that inherit this class will
    be automatically added to the list of built-ins. This should *not* be used
    for user-defined extensions.
    """


class CustomType(ExtensionType, metaclass=ExtensionTypeMeta):
    """
    Base class for all user-defined types.
    """

    # These attributes are duplicated here with docstrings since a bug in
    # sphinx prevents the docstrings of class attributes from being inherited
    # properly (see https://github.com/sphinx-doc/sphinx/issues/741). The
    # docstrings are not included anywhere else in the class hierarchy since
    # this class is the only one exposed in the public API.
    name = None
    """
    `str` or `list`: The name of the type.
    """

    organization = "stsci.edu"
    """
    `str`: The organization responsible for the type.
    """

    standard = "asdf"
    """
    `str`: The standard the type is defined in.
    """

    version = (1, 0, 0)
    """
    `str`, `tuple`, `asdf.versioning.AsdfVersion`, or `asdf.versioning.AsdfSpec`:
        The version of the type.
    """

    supported_versions = set()
    """
    `set`: Versions that explicitly compatible with this extension class.

    If provided, indicates explicit compatibility with the given set
    of versions. Other versions of the same schema that are not included in
    this set will not be converted to custom types with this class. """

    types = []
    """
    `list`: List of types that this extension class can convert to/from YAML.

    Custom Python types that, when found in the tree, will be converted into
    basic types for YAML output. Can be either strings referring to the types
    or the types themselves."""

    handle_dynamic_subclasses = False
    """
    `bool`: Indicates whether dynamically generated subclasses can be serialized

    Flag indicating whether this type is capable of serializing subclasses
    of any of the types listed in ``types`` that are generated dynamically.
    """

    validators = {}
    """
    `dict`: Mapping JSON Schema keywords to validation functions for jsonschema.

    Useful if the type defines extra types of validation that can be
    performed.
    """

    requires = []
    """
    `list`: Python packages that are required to instantiate the object.
    """

    yaml_tag = None
    """
    `str`: The YAML tag to use for the type.

    If not provided, it will be automatically generated from name,
    organization, standard and version.
    """

    has_required_modules = True
    """
    `bool`: Indicates whether modules specified by `requires` are available.

    NOTE: This value is automatically generated. Do not set it in subclasses as
    it will be overwritten.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Create a warning for a direct child of a CustomType class (not in grandchild)
        if CustomType in cls.__bases__:
            warnings.warn(
                f"{cls.__name__} from {cls.__module__} subclasses the deprecated CustomType class. "
                "Please see the new extension API "
                "https://asdf.readthedocs.io/en/stable/asdf/extending/converters.html",
                AsdfDeprecationWarning,
            )
