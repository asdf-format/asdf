from ..extension import ManifestExtension
from ._converters.complex import ComplexConverter
from ._converters.entities import (
    AsdfObjectConverter,
    ExtensionMetadataConverter,
    ExternalArrayReferenceConverter,
    HistoryEntryConverter,
    SoftwareConverter,
)
from ._converters.integer import IntegerConverter
from ._validators.ndarray import DatatypeValidator, MaxNdimValidator, NdimValidator

CONVERTERS = [
    AsdfObjectConverter(),
    ComplexConverter(),
    ExtensionMetadataConverter(),
    ExternalArrayReferenceConverter(),
    IntegerConverter(),
    HistoryEntryConverter(),
    SoftwareConverter(),
]


VALIDATORS = [
    NdimValidator(),
    MaxNdimValidator(),
    DatatypeValidator(),
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
