# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
import os

import pytest

import asdf
from asdf import schema

_ctx = AsdfFile()
_resolver = _ctx.resolver


def pytest_addoption(parser):
    parser.addini(
        "asdf_schema_root", "Root path indicating where schemas are stored")


class AsdfSchemaFile(pytest.File):
    def collect(self):
        yield AsdfSchemaItem(str(self.fspath), self, None)


class AsdfSchemaItem(pytest.Item):
    def __init__(self, schema_path, parent, spec):
        super(AsdfSchemaItem, self).__init__(schema_path, parent)
        self.schema_path = schema_path

    def runtest(self):
        # Make sure that each schema itself is valid.
        schema_tree = schema.load_schema(
            self.schema_path, resolver=_resolver, resolve_references=True)
        schema.check_schema(schema_tree)


def pytest_collect_file(path, parent):
    if path.ext == '.yaml':
        if path.purebasename in ['asdf-schema-1.0.0', 'draft-01']:
            return None

        return AsdfSchemaFile(path, parent)
