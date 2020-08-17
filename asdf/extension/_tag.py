class TagDefinition:
    """
    Container for properties of a custom YAML tag.

    Parameters
    ----------
    tag_uri : str
        Tag URI.
    schema_uri : str, optional
        URI of the schema that should be used to validate objects
        with this tag.
    title : str, optional
        Short description of the tag.
    description : str, optional
        Long description of the tag.
    """
    def __init__(self, tag_uri, *, schema_uri=None, title=None, description=None):
        if "*" in tag_uri:
            raise ValueError("URI patterns are not permitted in TagDefinition")

        self._tag_uri = tag_uri
        self._schema_uri = schema_uri
        self._title = title
        self._description = description

    @property
    def tag_uri(self):
        """
        Get the tag URI.

        Returns
        -------
        str
        """
        return self._tag_uri

    @property
    def schema_uri(self):
        """
        Get the URI of the schema that should be used to validate
        objects wtih this tag.

        Returns
        -------
        str or None
        """
        return self._schema_uri

    @property
    def title(self):
        """
        Get the short description of the tag.

        Returns
        -------
        str or None
        """
        return self._title

    @property
    def description(self):
        """
        Get the long description of the tag.

        Returns
        -------
        str or None
        """
        return self._description

    def __repr__(self):
        return ("<TagDefinition URI: {}>".format(self.tag_uri))
