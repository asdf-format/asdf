from asdf.extension import ManifestExtension

from ._converters.complex import ComplexConverter
from ._converters.constant import ConstantConverter
from ._converters.external_reference import ExternalArrayReferenceConverter
from ._converters.reference import ReferenceConverter
from ._converters.tree import (
    AsdfObjectConverter,
    ExtensionMetadataConverter,
    HistoryEntryConverter,
    SoftwareConverter,
    SubclassMetadataConverter,
)
from ._validators import ndarray

CONVERTERS = [
    ComplexConverter(),
    ConstantConverter(),
    ExternalArrayReferenceConverter(),
    AsdfObjectConverter(),
    ExtensionMetadataConverter(),
    HistoryEntryConverter(),
    SoftwareConverter(),
    SubclassMetadataConverter(),
    ReferenceConverter(),
]


VALIDATORS = [
    ndarray.NdimValidator(),
    ndarray.MaxNdimValidator(),
    ndarray.DatatypeValidator(),
]


MANIFEST_URIS = [
    "asdf://asdf-format.org/core/manifests/core-1.0.0",
    "asdf://asdf-format.org/core/manifests/core-1.1.0",
    "asdf://asdf-format.org/core/manifests/core-1.2.0",
    "asdf://asdf-format.org/core/manifests/core-1.3.0",
    "asdf://asdf-format.org/core/manifests/core-1.4.0",
    "asdf://asdf-format.org/core/manifests/core-1.5.0",
    "asdf://asdf-format.org/core/manifests/core-1.6.0",
]


EXTENSIONS = [ManifestExtension.from_uri(u, converters=CONVERTERS, validators=VALIDATORS) for u in MANIFEST_URIS]
