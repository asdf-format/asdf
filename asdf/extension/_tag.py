class TagDefinition:
    """
    Container for properties of a custom YAML tag.

    Parameters
    ----------
    tag_uri : str
        Tag URI.
    schema_uris : str, optional
        URI of the schema that should be used to validate objects
        with this tag.
    title : str, optional
        Short description of the tag.
    description : str, optional
        Long description of the tag.
    """

    def __init__(self, tag_uri, *, schema_uris=None, title=None, description=None):
        if "*" in tag_uri:
            msg = "URI patterns are not permitted in TagDefinition"
            raise ValueError(msg)

        self._tag_uri = tag_uri

        if schema_uris is None:
            self._schema_uris = []

        elif isinstance(schema_uris, list):
            self._schema_uris = schema_uris

        else:
            self._schema_uris = [schema_uris]

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
    def schema_uris(self):
        """
        Get the URIs of the schemas that should be used to validate
        objects with this tag.

        Returns
        -------
        list
        """
        return self._schema_uris

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
        return f"<TagDefinition URI: {self.tag_uri}>"
