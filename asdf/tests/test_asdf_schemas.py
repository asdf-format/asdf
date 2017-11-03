# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import io
import os
import re

import yaml
import pytest

import numpy as np

import astropy
from astropy.tests.helper import catch_warnings

import asdf
from asdf.tests import helpers, CustomTestType
from asdf import asdftypes
from asdf import block
from asdf import extension
from asdf import schema
from asdf import treeutil
from asdf import util
from asdf import versioning

try:
    import gwcs
    HAS_GWCS = True
except ImportError:
    HAS_GWCS = False


class LabelMapperTestType(CustomTestType):
    version = '1.0.0'
    name = 'transform/label_mapper'


class RegionsSelectorTestType(CustomTestType):
    version = '1.0.0'
    name = 'transform/regions_selector'


class TestExtension(extension.BuiltinExtension):
    """This class defines an extension that represents tags whose
    implementations current reside in other repositories (such as GWCS) but
    whose schemas are defined in ASDF. This provides a workaround for schema
    validation testing since we want to pass without warnings, but the fact
    that these tag classes are not defined within ASDF means that warnings
    occur unless this extension is used. Eventually these schemas may be moved
    out of ASDF and into other repositories, or ASDF will potentially provide
    abstract base classes for the tag implementations.
    """
    @property
    def types(self):
        return [LabelMapperTestType, RegionsSelectorTestType]

    @property
    def tag_mapping(self):
        return [('tag:stsci.edu:asdf',
                 'http://stsci.edu/schemas/asdf{tag_suffix}')]


def generate_schema_list():
    """Returns a generator for all schema files"""
    src = os.path.join(os.path.dirname(__file__), '../schemas')
    for root, dirs, files in os.walk(src):
        for fname in files:
            if not fname.endswith('.yaml'):
                continue
            if os.path.splitext(fname)[0] in (
                    'draft-01', 'asdf-schema-1.0.0'):
                continue
            yield os.path.join(root, fname)


def _assert_warnings(_warnings):
    if astropy.__version__ < '1.3.3':
        # Make sure at most only one warning occurred
        assert len(_warnings) <= 1, helpers.display_warnings(_warnings)
        # Make sure the warning was the one we expected
        if len(_warnings) == 1:
            message = str(_warnings[0].message)
            target_string = "gwcs and astropy-1.3.3 packages are required"
            assert message.startswith('Failed to convert'), \
                helpers.display_warnings(_warnings)
            assert target_string in str(_warnings[0].message), \
                helpers.display_warnings(_warnings)
    else:
        assert len(_warnings) == 0, helpers.display_warnings(_warnings)


def _find_standard_version(filename):
    components = filename[filename.find('schemas') + 1:].split(os.path.sep)
    tag = 'tag:{}:{}'.format(components[1], '/'.join(components[2:]))
    name, version = asdftypes.split_tag_version(tag.replace('.yaml', ''))

    for sv in versioning.supported_versions:
        map_version = versioning.get_version_map(sv)['tags'].get(name)
        if map_version is not None and version == map_version:
            return sv

    return versioning.default_version


def generate_example_schemas():
    """Returns a generator for all examples in schema files"""
    def find_examples_in_schema(path):
        """Returns generator for all examples in schema at given path"""
        with open(path, 'rb') as fd:
            schema_tree = yaml.load(fd)

        for node in treeutil.iter_tree(schema_tree):
            if (isinstance(node, dict) and
                'examples' in node and
                isinstance(node['examples'], list)):
                for desc, example in node['examples']:
                    yield example

    for schema_path in generate_schema_list():
        for example in find_examples_in_schema(schema_path):
            yield (schema_path, example)


def pytest_generate_tests(metafunc):
    """This function is used by pytest to parametrize test function inputs

    Parameters:
    -----------
    metafunc : object returned by pytest to enable test parametrization

    This function enables parametrization of the following tests:
        test_validate_schema
        test_schema_example

    The 'yield' functionality in pytest for parametrized tests has been
    deprecated. The @pytest.mark.parametrize decorator is not powerful enough
    for the kind of programmatic parametrization that we require here.
    """
    def get_schema_name(schema_path):
        """Helper function to return the informative part of a schema path"""
        path = os.path.normpath(schema_path)
        return os.path.sep.join(path.split(os.path.sep)[-3:])

    def create_schema_example_id(argval):
        """Helper function to create test ID for schema example validation"""
        if argval[0] == '/':
            # ID for the first argument is just the schema name
            return get_schema_name(argval)
        else:
            # This will cause pytest to create labels of the form:
            #   SCHEMA_NAME-example
            # If there are multiple examples within a single schema, the
            # examples will be numbered automatically to distinguish them
            return "example"

    if metafunc.function is test_validate_schema:
        metafunc.parametrize(
            'schema_path',
            generate_schema_list(),
            # just use the schema name as a test ID instead of full path
            ids=get_schema_name)
    elif metafunc.function is test_schema_example:
        metafunc.parametrize(
            'filename,example',
            generate_example_schemas(),
            ids=create_schema_example_id)


def test_validate_schema(schema_path):
    """Pytest to check validity of schema file at given path

    Parameters:
    -----------
    schema_path : name of the schema file to be validated

    This function is called with a range of parameters by pytest's
    'parametrize' utility in order to account for all schema files.
    """
    # Make sure that each schema itself is valid.
    schema_tree = schema.load_schema(schema_path, resolve_references=True)
    schema.check_schema(schema_tree)


def test_schema_example(filename, example):
    """Pytest to check validity of a specific example within schema file

    Parameters:
    -----------
    filename : name of the schema file containing example to be tested

    example: string representing example

    This function is called with a range of parameters by pytest's
    'parametrize' utility in order to account for all examples in all schema
    files.
    """
    if not HAS_GWCS and re.search(r'frame-\d\.\d\.\d\.yaml', filename):
        return pytest.skip

    standard_version = _find_standard_version(filename)

    # Make sure that the examples in the schema files (and thus the
    # ASDF standard document) are valid.
    buff = helpers.yaml_to_asdf(
        'example: ' + example.strip(), standard_version=standard_version)
    ff = asdf.AsdfFile(
        uri=util.filepath_to_url(os.path.abspath(filename)),
        extensions=TestExtension())

    # Fake an external file
    ff2 = asdf.AsdfFile({'data': np.empty((1024*1024*8), dtype=np.uint8)})

    ff._external_asdf_by_uri[
        util.filepath_to_url(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(filename), 'external.asdf')))] = ff2

    # Add some dummy blocks so that the ndarray examples work
    for i in range(3):
        b = block.Block(np.zeros((1024*1024*8), dtype=np.uint8))
        b._used = True
        ff.blocks.add(b)
    b._array_storage = "streamed"

    try:
        with catch_warnings() as w:
            ff._open_impl(ff, buff)
        # Do not tolerate any warnings that occur during schema validation,
        # other than a few that we expect to occur under certain circumstances
        _assert_warnings(w)
    except:
        print("From file:", filename)
        raise

    # Just test we can write it out.  A roundtrip test
    # wouldn't always yield the correct result, so those have
    # to be covered by "real" unit tests.
    if b'external.asdf' not in buff.getvalue():
        buff = io.BytesIO()
        ff.write_to(buff)
