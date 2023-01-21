import abc


class Validator(abc.ABC):
    """
    Abstract base class for plugins that handle custom validators
    in ASDF schemas.
    """

    @abc.abstractproperty
    def schema_property(self):
        """
        Name of the schema property used to invoke this validator.
        """

    @abc.abstractproperty
    def tags(self):
        """
        Get the YAML tags that are appropriate to this validator.
        URI patterns are permitted, see `asdf.util.uri_match` for details.

        Returns
        -------
        iterable of str
            Tag URIs or URI patterns.
        """

    @abc.abstractmethod
    def validate(self, schema_property_value, node, schema):
        """
        Validate the given node from the ASDF tree.

        Parameters
        ----------
        schema_property_value : object
            The value assigned to the schema property associated with this
            valdiator.

        node : asdf.tagged.Tagged
            A tagged node from the tree.  Guaranteed to bear a tag that
            matches one of the URIs returned by this validator's tags property.

        schema : dict
            The schema object that contains the property that triggered
            the validation.  Typically implementations of this method do
            not need to make use of this object, but sometimes the behavior
            of a validator depends on other schema properties.  An example is
            the built-in "additionalProperties" property, which needs to know
            the contents of the "properties" property in order to determine
            which node properties are additional.

        Yields
        ------
        asdf.exceptions.ValidationError
            Yield an instance of ValidationError for each error present in the node.
        """
