from functools import lru_cache

from asdf.tagged import Tagged
from asdf.util import get_class_name, uri_match

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

        validators = set()

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

            validators.update(extension.validators)

        self._validator_manager = _get_cached_validator_manager(tuple(validators))

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
            msg = f"No support available for YAML tag '{tag}'.  You may need to install a missing extension."
            raise KeyError(msg) from None

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
            msg = f"No support available for YAML tag '{tag}'.  You may need to install a missing extension."
            raise KeyError(msg) from None

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
                msg = (
                    f"No support available for Python type '{get_class_name(typ, instance=False)}'.  "
                    "You may need to install or enable an extension."
                )
                raise KeyError(msg) from None

    @property
    def validator_manager(self):
        return self._validator_manager


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


class ValidatorManager:
    """
    Wraps a list of custom validators and indexes them by schema property.

    Parameters
    ----------
    validators : iterable of asdf.extension.Validator
        List of validators to manage.
    """

    def __init__(self, validators):
        self._validators = list(validators)

        self._validators_by_schema_property = {}
        for validator in self._validators:
            if validator.schema_property not in self._validators_by_schema_property:
                self._validators_by_schema_property[validator.schema_property] = set()
            self._validators_by_schema_property[validator.schema_property].add(validator)

        self._jsonschema_validators_by_schema_property = {}
        for schema_property in self._validators_by_schema_property:
            self._jsonschema_validators_by_schema_property[schema_property] = self._get_jsonschema_validator(
                schema_property,
            )

    def validate(self, schema_property, schema_property_value, node, schema):
        """
        Validate an ASDF tree node against custom validators for a schema property.

        Parameters
        ----------
        schema_property : str
            Name of the schema property (identifies the validator(s) to use).
        schema_property_value : object
            Value of the schema property.
        node : asdf.tagged.Tagged
            The ASDF node to validate.
        schema : dict
            The schema object that contains the property that triggered
            the validation.

        Yields
        ------
        asdf.exceptions.ValidationError
        """
        if schema_property in self._validators_by_schema_property:
            for validator in self._validators_by_schema_property[schema_property]:
                if _validator_matches(validator, node):
                    yield from validator.validate(schema_property_value, node, schema)

    def get_jsonschema_validators(self):
        """
        Get a dictionary of validator methods suitable for use
        with the jsonschema library.

        Returns
        -------
        dict of str: callable
        """
        return dict(self._jsonschema_validators_by_schema_property)

    def _get_jsonschema_validator(self, schema_property):
        def _validator(_, schema_property_value, node, schema):
            return self.validate(schema_property, schema_property_value, node, schema)

        return _validator


def _validator_matches(validator, node):
    if any(t == "**" for t in validator.tags):
        return True

    if not isinstance(node, Tagged):
        return False

    return any(uri_match(t, node._tag) for t in validator.tags)


@lru_cache
def _get_cached_validator_manager(validators):
    return ValidatorManager(validators)
