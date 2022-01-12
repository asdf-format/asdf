from dataclasses import dataclass
from typing import Tuple, Union


@dataclass
class ExternalArrayReference:
    """
    Store a reference to an array in an external File.

    This class is a simple way of referring to an array in another file. It
    provides no way to resolve these references, that is left to the user. It
    also performs no checking to see if any of the arguments are correct. e.g.
    if the file exits.

    Parameters
    ----------

    fileuri: str
        The path to the path to be referenced. Can be relative to the file
        containing the reference.

    target: str or int
        Some internal target to the data in the file. Examples may include a HDU
        index, a HDF path or an asdf fragment.

    dtype: str
        The (numpy) dtype of the contained array.

    shape: tuple of int
        The shape of the array to be loaded.


    Examples
    --------

    >>> import asdf
    >>> ref = asdf.core.ExternalArrayReference("myfitsfile.fits", 1, "float64", (100, 100))
    >>> tree = {'reference': ref}
    >>> with asdf.AsdfFile(tree) as ff:
    ...     ff.write_to("test.asdf")

    """
    fileuri: str
    target: Union[str, int]
    datatype: str
    shape: Tuple[int]
