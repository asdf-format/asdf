# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
import io
import os
from importlib.util import find_spec
from pkg_resources import parse_version

import yaml
import pytest

import numpy as np

# Avoid all imports of asdf at this level in order to avoid circular imports


def pytest_addoption(parser):
    parser.addini(
        "asdf_schema_root", "Root path indicating where schemas are stored")
    parser.addini(
        "asdf_schema_skip_names", "Base names of files to skip in schema tests")
    parser.addini(
        "asdf_schema_skip_examples",
        "Base names of schemas whose examples should not be tested")
    parser.addini(
        "asdf_schema_tests_enabled",
        "Controls whether schema tests are enabled by default",
        type="bool",
        default=False,
    )
    parser.addini(
        "asdf_schema_ignore_unrecognized_tag",
        "Set to true to disable warnings when tag serializers are missing",
        type="bool",
        default=False,
    )
    parser.addoption('--asdf-tests', action='store_true',
        help='Enable ASDF schema tests')


class AsdfSchemaFile(pytest.File):
    @classmethod
    def from_parent(cls, parent, *, fspath, skip_examples=False, ignore_unrecognized_tag=False, **kwargs):
        if hasattr(super(), "from_parent"):
            result = super().from_parent(parent, fspath=fspath, **kwargs)
        else:
            result = AsdfSchemaFile(fspath, parent, **kwargs)

        result.skip_examples = skip_examples
        result.ignore_unrecognized_tag = ignore_unrecognized_tag
        return result

    def collect(self):
        yield AsdfSchemaItem.from_parent(self, self.fspath)
        if not self.skip_examples:
            for example in self.find_examples_in_schema():
                yield AsdfSchemaExampleItem.from_parent(
                    self,
                    self.fspath,
                    example,
                    ignore_unrecognized_tag=self.ignore_unrecognized_tag
                )

    def find_examples_in_schema(self):
        """Returns generator for all examples in schema at given path"""
        from asdf import treeutil

        with open(str(self.fspath), 'rb') as fd:
            schema_tree = yaml.safe_load(fd)

        for node in treeutil.iter_tree(schema_tree):
            if (isinstance(node, dict) and
                'examples' in node and
                isinstance(node['examples'], list)):
                for desc, example in node['examples']:
                    yield example


class AsdfSchemaItem(pytest.Item):
    @classmethod
    def from_parent(cls, parent, schema_path, **kwargs):
        if hasattr(super(), "from_parent"):
            result = super().from_parent(parent, name=str(schema_path), **kwargs)
        else:
            result = AsdfSchemaItem(str(schema_path), parent, **kwargs)

        result.schema_path = schema_path
        return result

    def runtest(self):
        from asdf import schema
        from asdf.extension import default_extensions

        # Make sure that each schema itself is valid.
        schema_tree = schema.load_schema(
            self.schema_path, resolver=default_extensions.resolver,
            resolve_references=True)
        schema.check_schema(schema_tree)


ASTROPY_4_0_TAGS = {
    'tag:stsci.edu:asdf/transform/rotate_sequence_3d',
    'tag:stsci.edu:asdf/transform/ortho_polynomial',
    'tag:stsci.edu:asdf/transform/fix_inputs',
    'tag:stsci.edu:asdf/transform/math_functions',
    'tag:stsci.edu:asdf/time/time',
}


def should_skip(name, version):
    if name == 'tag:stsci.edu:asdf/transform/multiplyscale':
        return not is_min_astropy_version('3.1.dev0')
    elif name in ASTROPY_4_0_TAGS:
        return not is_min_astropy_version('4.0')

    return False


def is_min_astropy_version(min_version):
    astropy = find_spec('astropy')
    if astropy is None:
        return False

    import astropy
    return parse_version(astropy.version.version) >= parse_version(min_version)


def parse_schema_filename(filename):
    from asdf import versioning
    components = filename[filename.find('schemas') + 1:].split(os.path.sep)
    tag = 'tag:{}:{}'.format(components[1], '/'.join(components[2:]))
    name, version = versioning.split_tag_version(tag.replace('.yaml', ''))
    return name, version


class AsdfSchemaExampleItem(pytest.Item):
    @classmethod
    def from_parent(cls, parent, schema_path, example, ignore_unrecognized_tag=False, **kwargs):
        test_name = "{}-example".format(schema_path)
        if hasattr(super(), "from_parent"):
            result = super().from_parent(parent, name=test_name, **kwargs)
        else:
            result = AsdfSchemaExampleItem(test_name, parent, **kwargs)
        result.filename = str(schema_path)
        result.example = example
        result.ignore_unrecognized_tag = ignore_unrecognized_tag
        return result

    def _find_standard_version(self, name, version):
        from asdf import versioning
        for sv in reversed(versioning.supported_versions):
            map_version = versioning.get_version_map(sv)['tags'].get(name)
            if map_version is not None and version == map_version:
                return sv

        return versioning.default_version

    def runtest(self):
        from asdf import AsdfFile, block, util
        from asdf.tests import helpers

        name, version = parse_schema_filename(self.filename)
        if should_skip(name, version):
            return

        standard_version = self._find_standard_version(name, version)

        # Make sure that the examples in the schema files (and thus the
        # ASDF standard document) are valid.
        buff = helpers.yaml_to_asdf(
            'example: ' + self.example.strip(), standard_version=standard_version)
        ff = AsdfFile(
            uri=util.filepath_to_url(os.path.abspath(self.filename)),
            ignore_unrecognized_tag=self.ignore_unrecognized_tag,
        )

        # Fake an external file
        ff2 = AsdfFile({'data': np.empty((1024*1024*8), dtype=np.uint8)})

        ff._external_asdf_by_uri[
            util.filepath_to_url(
                os.path.abspath(
                    os.path.join(
                        os.path.dirname(self.filename), 'external.asdf')))] = ff2

        # Add some dummy blocks so that the ndarray examples work
        for i in range(3):
            b = block.Block(np.zeros((1024*1024*8), dtype=np.uint8))
            b._used = True
            ff.blocks.add(b)
        b._array_storage = "streamed"

        try:
            with pytest.warns(None) as w:
                ff._open_impl(ff, buff, mode='rw')
            # Do not tolerate any warnings that occur during schema validation
            assert len(w) == 0, helpers.display_warnings(w)
        except Exception:
            print("From file:", self.filename)
            raise

        # Just test we can write it out.  A roundtrip test
        # wouldn't always yield the correct result, so those have
        # to be covered by "real" unit tests.
        if b'external.asdf' not in buff.getvalue():
            buff = io.BytesIO()
            ff.write_to(buff)


def pytest_collect_file(path, parent):
    if not (parent.config.getini('asdf_schema_tests_enabled') or
            parent.config.getoption('asdf_tests')):
        return

    schema_roots = parent.config.getini('asdf_schema_root').split()
    if not schema_roots:
        return

    skip_names = parent.config.getini('asdf_schema_skip_names')
    skip_examples = parent.config.getini('asdf_schema_skip_examples')
    ignore_unrecognized_tag = parent.config.getini('asdf_schema_ignore_unrecognized_tag')

    schema_roots = [os.path.join(str(parent.config.rootdir), os.path.normpath(root))
                        for root in schema_roots]

    if path.ext != '.yaml':
        return None

    for root in schema_roots:
        if str(path).startswith(root) and path.purebasename not in skip_names:
            return AsdfSchemaFile.from_parent(
                parent,
                fspath=path,
                skip_examples=(path.purebasename in skip_examples),
                ignore_unrecognized_tag=ignore_unrecognized_tag,
            )

    return None
