from asdf.extension import ManifestExtension

from ._validators import ndarray

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


EXTENSIONS = [ManifestExtension.from_uri(u, validators=VALIDATORS) for u in MANIFEST_URIS]
