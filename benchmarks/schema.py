import numpy

import asdf


class SoftwareValidateSuite:
    def setup(self):
        # software is a pretty simple tag, so validation should be fast
        s = asdf.tags.core.Software(name="foo", version="0.0.0")
        self.af = asdf.AsdfFile()
        self.af["i"] = s
        self.obj = dict(asdf.yamlutil.custom_tree_to_tagged_tree(self.af.tree, self.af)["i"])
        self.schema = asdf.schema.load_schema(
            "http://stsci.edu/schemas/asdf/core/software-1.0.0",
            resolve_references=True,
        )

    def time_validate(self):
        self.af.validate()


class NDArrayValidateSuite:
    def setup(self):
        # ndarray is more complicated and validation will be slower
        n = numpy.ndarray([1])
        self.af = asdf.AsdfFile()
        self.af["i"] = n
        self.obj = dict(asdf.yamlutil.custom_tree_to_tagged_tree(self.af.tree, self.af)["i"])
        self.schema = asdf.schema.load_schema(
            "http://stsci.edu/schemas/asdf/core/ndarray-1.0.0",
            resolve_references=True,
        )

    def time_validate(self):
        self.af.validate()
