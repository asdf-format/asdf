import abc

__all__ = ["_AsdfExtension"]


class _AsdfExtension(metaclass=abc.ABCMeta):
    """
    Abstract base class defining a (legacy) extension to ASDF.
    New code should use `asdf.extension.Extension` instead.
    """

    @classmethod
    def __subclasshook__(cls, class_):
        if cls is _AsdfExtension:
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
