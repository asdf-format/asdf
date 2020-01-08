from ...types import AsdfType


class ExternalArrayReference(AsdfType):
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
    name = "core/externalarray"
    version = (1, 0, 0)

    def __init__(self, fileuri, target, dtype, shape):
        self.fileuri = str(fileuri)
        self.target = target
        self.dtype = dtype
        self.shape = tuple(shape)

    def __repr__(self):
        return "<External array reference in {0} at {1} shape: {2} dtype: {3}>".format(
            self.fileuri, self.target, self.shape, self.dtype)

    def __str__(self):
        return repr(self)

    def __eq__(self, other):
        uri = self.fileuri == other.fileuri
        target = self.target == other.target
        dtype = self.dtype == other.dtype
        shape = self.shape == other.shape

        return all((uri, target, dtype, shape))

    @classmethod
    def to_tree(self, data, ctx):
        node = {}
        node['fileuri'] = data.fileuri
        node['target'] = data.target
        node['datatype'] = data.dtype
        node['shape'] = data.shape

        return node

    @classmethod
    def from_tree(cls, tree, ctx):
        return cls(tree['fileuri'], tree['target'], tree['datatype'], tree['shape'])



class ExternalArrayReferenceCollection(AsdfType):
    """
    A homogeneous collection of `asdf.ExternalArrayReference` like objects.

    This class differs from a list of `asdf.ExternalArrayReference` objects
    because all of the references have the same shape, dtype and target. This
    allows for much more yaml and schema efficient storage in the asdf tree.

    Parameters
    ----------

    fileuris: `list` or `tuple`
        An interable of paths to be referenced. Can be nested arbitarily deep.

    target: `object`
        Some internal target to the data in the files. Examples may include a HDU
        index, a HDF path or an asdf fragment.

    dtype: `str`
        The (numpy) dtype of the contained arrays.

    shape: `tuple`
        The shape of the arrays to be loaded.
    """
    name = "core/externalarrayreference"
    version = (1, 0, 0)

    @classmethod
    def _validate_homogenaity(cls, shape, target, dtype, ear):
        """
        Ensure that if constructing from `asdf.ExternalArrayReference` objects
        all of them have the same shape, dtype and target.
        """
        if isinstance(ears, (list, tuple)):
            return list(map(partial(cls._validate_homogenaity, shape, target, dtype), ear))

        if not isinstance(ear, ExternalArrayReference):
            raise TypeError("Every element of must be an instance of ExternalArrayReference.")
        if ear.dtype != dtype:
            raise ValueError(f"The Reference {ear} does not have the same dtype as the first reference.")
        if ear.shape != shape:
            raise ValueError(f"The Reference {ear} does not have the same shape as the first reference.")
        if ear.target != target:
            raise ValueError(f"The Reference {ear} does not have the same target as the first reference.")
        return ear.fileuri

    @classmethod
    def from_external_array_references(cls, ears):
        """
        Construct a collection from a (nested) iterable of
        `asdf.ExternalArrayReference` objects.
        """
        shape = ears[0].shape
        dtype = ears[0].dtype
        target = ears[0].target

        for i, ele in enumerate(ears):
            uris = cls._validate_homogenaity(shape, target, dtype, ears)

        return cls(uris, target, dtype, shape)

    def __init__(self, fileuris, target, dtype, shape):
        self.shape = tuple(shape)
        self.dtype = dtype
        self.target = target
        self.fileuris = fileuris

    def _to_ears(self, urilist):
        if isinstance(urilist, (list, tuple)):
            return list(map(self._to_ears, urilist))
        return ExternalArrayReference(urilist, self.target, self.dtype, self.shape)

    @property
    def external_array_references(self):
        """
        Represent this collection as a list of `asdf.ExternalArrayReference` objects.
        """
        return self._to_ears(self.fileuris)

    def __getitem__(self, item):
        uris = self.fileuris[item]
        if isinstance(uris, str):
            uris = [uris]
        return type(self)(uris, self.target, self.dtype, self.shape)

    def __len__(self):
        return len(self.fileuris)

    def __eq__(self, other):
        uri = self.fileuris == other.fileuris
        target = self.target == other.target
        dtype = self.dtype == other.dtype
        shape = self.shape == other.shape

        return all((uri, target, dtype, shape))

    @classmethod
    def to_tree(self, data, ctx):
        node = {}
        node['fileuris'] = data.fileuris
        node['target'] = data.target
        node['datatype'] = data.dtype
        node['shape'] = data.shape
        return node

    @classmethod
    def from_tree(cls, tree, ctx):
        return cls(tree['fileuris'], tree['target'], tree['datatype'], tree['shape'])
