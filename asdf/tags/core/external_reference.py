class ExternalArrayReference:
    """
    Store a reference to an array in an external File.

    This class is a simple way of referring to an array in another file. It
    provides no way to resolve these references, that is left to the user. It
    also performs no checking to see if any of the arguments are correct. e.g.
    if the file exits.

    Parameters
    ----------

    fileuri: `str`
        The path to the path to be referenced. Can be relative to the file
        containing the reference.

    target: `object`
        Some internal target to the data in the file. Examples may include a HDU
        index, a HDF path or an asdf fragment.

    dtype: `str`
        The (numpy) dtype of the contained array.

    shape: `tuple`
        The shape of the array to be loaded.


    Examples
    --------

    >>> import asdf
    >>> ref = asdf.ExternalArrayReference("myfitsfile.fits", 1, "float64", (100, 100))
    >>> tree = {'reference': ref}
    >>> with asdf.AsdfFile(tree) as ff:
    ...     ff.write_to("test.asdf")

    """

    def __init__(self, fileuri, target, dtype, shape):
        self.fileuri = str(fileuri)
        self.target = target
        self.dtype = dtype
        self.shape = tuple(shape)

    def __repr__(self):
        return f"<External array reference in {self.fileuri} at {self.target} shape: {self.shape} dtype: {self.dtype}>"

    def __str__(self):
        return repr(self)

    def __eq__(self, other):
        uri = self.fileuri == other.fileuri
        target = self.target == other.target
        dtype = self.dtype == other.dtype
        shape = self.shape == other.shape

        return all((uri, target, dtype, shape))
