import yaml

from ._extension import Extension
from ._tag import TagDefinition


class ManifestExtension(Extension):
    """
    Extension implementation that reads the extension URI, ASDF
    Standard requirement, and tag list from a manifest document.

    Parameters
    ----------
    manifest : dict
        Parsed manifest.
    converters : iterable of asdf.extension.Converter, optional
        Converter instances for the tags and Python types
        supported by this extension.
    legacy_class_names : iterable of str, optional
        Fully-qualified class names used by older versions
        of this extension.
    """
    @classmethod
    def from_uri(cls, manifest_uri, **kwargs):
        """
        Construct the extension using the manifest with the
        specified URI.  The manifest document must be registered
        with ASDF's resource manager.

        Parameters
        ----------
        manifest_uri : str
            Manifest URI.

        See the class docstring for details on keyword parameters.
        """
        from ..config import get_config
        manifest = yaml.safe_load(get_config().resource_manager[manifest_uri])
        return cls(manifest, **kwargs)

    def __init__(self, manifest, *, legacy_class_names=None, converters=None,
                compressors=None, decompressors=None):
        self._manifest = manifest

        if legacy_class_names is None:
            self._legacy_class_names = []
        else:
            self._legacy_class_names = legacy_class_names

        if converters is None:
            self._converters = []
        else:
            self._converters = converters

        if compressors is None:
            self._compressors = []
        else:
            self._compressors = compressors

        if decompressors is None:
            self._decompressors = []
        else:
            self._decompressors = decompressors

    @property
    def extension_uri(self):
        return self._manifest["extension_uri"]

    @property
    def legacy_class_names(self):
        return self._legacy_class_names

    @property
    def asdf_standard_requirement(self):
        version = self._manifest.get("asdf_standard_requirement", None)
        if version is None:
            return None
        elif isinstance(version, str):
            return "=={}".format(version)
        else:
            specifiers = []
            for prop, operator in [("gt", ">"), ("gte", ">="), ("lt", "<"), ("lte", "<=")]:
                value = version.get(prop)
                if value:
                    specifiers.append("{}{}".format(operator, value))
            return ",".join(specifiers)

    @property
    def converters(self):
        return self._converters

    @property
    def compressors(self):
        return self._compressors

    @property
    def decompressors(self):
        return self._decompressors

    @property
    def tags(self):
        result = []
        for tag in self._manifest.get("tags", []):
            if isinstance(tag, str):
                # ExtensionProxy knows how to handle str tags.
                result.append(tag)
            elif isinstance(tag, dict):
                result.append(
                    TagDefinition(
                        tag["tag_uri"],
                        schema_uri=tag.get("schema_uri"),
                        title=tag.get("title"),
                        description=tag.get("description"),
                    )
                )
            else:
                raise TypeError("Malformed manifest document")
        return result
