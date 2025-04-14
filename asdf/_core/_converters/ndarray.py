import numpy as np

from asdf.extension import Converter


class NDArrayConverter(Converter):
    tags = [
        "tag:stsci.edu:asdf/core/ndarray-1.0.0",
        "tag:stsci.edu:asdf/core/ndarray-1.1.0",
    ]
    types = [
        np.ndarray,  # we use the type here so the extension can find the sub-classes
        "numpy.ma.MaskedArray",  # in numpy 2.0
        "numpy.ma.core.MaskedArray",
        "asdf.tags.core.ndarray.NDArrayType",
        "asdf.tags.core.stream.Stream",
    ]

    def to_yaml_tree(self, obj, tag, ctx):
        import numpy as np
        from numpy import ma

        from asdf import config, util
        from asdf._block.options import Options
        from asdf.tags.core.ndarray import NDArrayType, numpy_array_to_list, numpy_dtype_to_asdf_datatype
        from asdf.tags.core.stream import Stream

        data = obj

        if isinstance(obj, Stream):
            # previously, stream never passed on data, we can do that here
            ctx._blocks.set_streamed_write_block(data._array, data)

            result = {}
            result["source"] = -1
            result["shape"] = ["*", *data._shape]
            result["datatype"] = data._datatype
            result["byteorder"] = data._byteorder
            if data._strides is not None:
                result["strides"] = data._strides
            return result

        # sort out block writing options
        if isinstance(obj, NDArrayType) and isinstance(obj._source, str):
            # this is an external block, if we have no other settings, keep it as external
            options = ctx._blocks.options.lookup_by_object(data)
            if options is None:
                options = Options("external")
        else:
            options = ctx._blocks.options.get_options(data)

        # The ndarray-1.0.0 schema does not permit 0 valued strides.
        # Perhaps we'll want to allow this someday, to efficiently
        # represent an array of all the same value.
        if any(stride == 0 for stride in data.strides):
            data = np.ascontiguousarray(data)

        # Use the base array if that option is set or if the option
        # is unset and the AsdfConfig default is set
        cfg = config.get_config()
        if options.save_base or (options.save_base is None and cfg.default_array_save_base):
            base = util.get_array_base(data)
        else:
            base = data

        # The view computations that follow assume that the base array
        # is contiguous.  If not, we need to make a copy to avoid
        # writing a nonsense view.
        if not base.flags.forc:
            data = np.ascontiguousarray(data)
            base = util.get_array_base(data)

        shape = data.shape

        # possibly override options based on config settings
        if cfg.all_array_storage is not None:
            options.storage_type = cfg.all_array_storage
        if cfg.all_array_compression != "input":
            options.compression = cfg.all_array_compression
            options.compression_kwargs = cfg.all_array_compression_kwargs
        inline_threshold = cfg.array_inline_threshold

        if inline_threshold is not None and options.storage_type in ("inline", "internal"):
            if data.size < inline_threshold:
                options.storage_type = "inline"
            else:
                options.storage_type = "internal"
        ctx._blocks.options.set_options(data, options)

        # Compute the offset relative to the base array and not the
        # block data, in case the block is compressed.
        offset = data.ctypes.data - base.ctypes.data

        strides = None if data.flags.c_contiguous else data.strides
        dtype, byteorder = numpy_dtype_to_asdf_datatype(
            data.dtype,
            include_byteorder=(options.storage_type != "inline"),
        )

        result = {}

        result["shape"] = list(shape)
        if options.storage_type == "streamed":
            result["shape"][0] = "*"

        if options.storage_type == "inline":
            listdata = numpy_array_to_list(data)
            result["data"] = listdata
            result["datatype"] = dtype

        else:
            result["shape"] = list(shape)
            if options.storage_type == "streamed":
                result["shape"][0] = "*"
                result["source"] = -1
                ctx._blocks.set_streamed_write_block(base, data)
            else:
                result["source"] = ctx._blocks.make_write_block(base, options, obj)
            result["datatype"] = dtype
            result["byteorder"] = byteorder

            if offset > 0:
                result["offset"] = offset

            if strides is not None:
                result["strides"] = list(strides)

        if isinstance(data, ma.MaskedArray):
            if options.storage_type == "inline":
                ctx._blocks._set_array_storage(data.mask, "inline")

            result["mask"] = data.mask

        return result

    def from_yaml_tree(self, node, tag, ctx):
        import sys
        import weakref

        from asdf.tags.core import NDArrayType
        from asdf.tags.core.ndarray import asdf_datatype_to_numpy_dtype

        if isinstance(node, list):
            instance = NDArrayType(node, None, None, None, None, None, None)
            ctx._blocks._set_array_storage(instance, "inline")
            if not ctx._blocks._lazy_load:
                return instance._make_array()
            return instance

        if isinstance(node, dict):
            shape = node.get("shape", None)
            if "source" in node and "data" in node:
                msg = "Both source and data may not be provided at the same time"
                raise ValueError(msg)
            if "source" in node:
                source = node["source"]
                byteorder = node["byteorder"]
            else:
                source = node["data"]
                byteorder = sys.byteorder
            dtype = asdf_datatype_to_numpy_dtype(node["datatype"], byteorder) if "datatype" in node else None
            offset = node.get("offset", 0)
            strides = node.get("strides", None)
            mask = node.get("mask", None)

            if isinstance(source, int):
                # internal block
                data_callback = ctx.get_block_data_callback(source)
                instance = NDArrayType(source, shape, dtype, offset, strides, "A", mask, data_callback)
            elif isinstance(source, str):
                # external
                def data_callback(_attr=None, _ref=weakref.ref(ctx._blocks)):
                    if _attr not in (None, "cached_data", "data"):
                        raise AttributeError(f"_attr {_attr} is not supported")
                    blks = _ref()
                    if blks is None:
                        msg = "Failed to resolve reference to AsdfFile to read external block"
                        raise OSError(msg)
                    array = blks._load_external(source)
                    blks._set_array_storage(array, "external")
                    return array

                instance = NDArrayType(source, shape, dtype, offset, strides, "A", mask, data_callback)
            else:
                # inline
                instance = NDArrayType(source, shape, dtype, offset, strides, "A", mask)
                ctx._blocks._set_array_storage(instance, "inline")

            if not ctx._blocks._lazy_load:
                return instance._make_array()
            return instance

        msg = "Invalid ndarray description."
        raise TypeError(msg)

    def to_info(self, obj):
        return {"shape": obj.shape, "dtype": obj.dtype}
