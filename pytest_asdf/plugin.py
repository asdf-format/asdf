import importlib
import os
import pathlib
from dataclasses import dataclass

import pytest
import yaml

# Avoid all imports of asdf at this level in order to avoid circular imports
HAS_NEW_PLUGIN = importlib.util.find_spec("pytest_asdf_plugin") is not None


def pytest_addoption(parser):
    if HAS_NEW_PLUGIN:
        return
    parser.addini("asdf_schema_root", "Root path indicating where schemas are stored")
    parser.addini("asdf_schema_skip_names", "Base names of files to skip in schema tests")
    parser.addini(
        "asdf_schema_skip_tests",
        "List of tests to skip, one per line, in format <schema path suffix>::<test name>",
    )
    parser.addini(
        "asdf_schema_xfail_tests",
        "List of tests to xfail, one per line, in format <schema path suffix>::<test name>",
    )
    parser.addini("asdf_schema_skip_examples", "Base names of schemas whose examples should not be tested")
    parser.addini(
        "asdf_schema_tests_enabled",
        "Controls whether schema tests are enabled by default",
        type="bool",
        default=False,
    )
    parser.addini(
        "asdf_schema_validate_default",
        "Set to true to enable validation of the schema 'default' property",
        type="bool",
        default=True,
    )
    parser.addini(
        "asdf_schema_ignore_unrecognized_tag",
        "Set to true to disable warnings when tag serializers are missing",
        type="bool",
        default=False,
    )
    parser.addoption("--asdf-tests", action="store_true", help="Enable ASDF schema tests")


class AsdfSchemaFile(pytest.File):
    @classmethod
    def from_parent(
        cls,
        parent,
        *,
        fspath,
        skip_examples=False,
        validate_default=True,
        ignore_unrecognized_tag=False,
        skip_tests=None,
        xfail_tests=None,
        **kwargs,
    ):
        path = pathlib.Path(fspath)
        kwargs["path"] = path

        if hasattr(super(), "from_parent"):
            result = super().from_parent(parent, **kwargs)
        else:
            result = AsdfSchemaFile(path, parent)

        result.skip_examples = skip_examples
        result.validate_default = validate_default
        result.ignore_unrecognized_tag = ignore_unrecognized_tag
        result.skip_tests = [] if skip_tests is None else skip_tests
        result.xfail_tests = [] if xfail_tests is None else xfail_tests

        return result

    def _set_markers(self, item):
        if item.name in self.skip_tests or "*" in self.skip_tests:
            item.add_marker(pytest.mark.skip)
        if item.name in self.xfail_tests or "*" in self.xfail_tests:
            item.add_marker(pytest.mark.xfail)

    def collect(self):
        item = AsdfSchemaItem.from_parent(self, self.fspath, validate_default=self.validate_default, name="test_schema")
        self._set_markers(item)
        yield item

        if not self.skip_examples:
            for index, example in enumerate(self.find_examples_in_schema()):
                name = f"test_example_{index}"
                item = AsdfSchemaExampleItem.from_parent(
                    self,
                    self.fspath,
                    example,
                    index,
                    ignore_unrecognized_tag=self.ignore_unrecognized_tag,
                    name=name,
                )
                self._set_markers(item)
                yield item

    def find_examples_in_schema(self):
        """Returns generator for all examples in schema at given path"""
        from asdf import treeutil

        with open(str(self.fspath), "rb") as fd:
            schema_tree = yaml.safe_load(fd)

        for node in treeutil.iter_tree(schema_tree):
            if isinstance(node, dict) and "examples" in node and isinstance(node["examples"], list):
                yield from node["examples"]


class AsdfSchemaItem(pytest.Item):
    @classmethod
    def from_parent(cls, parent, schema_path, validate_default=True, **kwargs):
        if hasattr(super(), "from_parent"):
            result = super().from_parent(parent, **kwargs)
        else:
            name = kwargs.pop("name")
            result = AsdfSchemaItem(name, parent, **kwargs)

        result.schema_path = schema_path
        result.validate_default = validate_default
        return result

    def runtest(self):
        from asdf import schema

        # Make sure that each schema itself is valid.
        schema_tree = schema.load_schema(
            self.schema_path,
            resolve_references=True,
        )
        schema.check_schema(schema_tree, validate_default=self.validate_default)

    def reportinfo(self):
        return self.fspath, 0, ""


@dataclass
class SchemaExample:
    description: str
    example: str
    _version: str = None
    other: any = None

    @classmethod
    def from_schema(cls, example: list):
        if len(example) == 1:
            _description = ""
            _example = example[0]
        elif len(example) == 2:
            _description = example[0]
            _example = example[1]
            _version = None
            _other = None
        elif len(example) > 2:
            _description = example[0]
            _example = example[2]
            _version = example[1]
            _other = example[3:] if len(example) > 3 else None
        else:
            msg = "Invalid example"
            raise RuntimeError(msg)

        return cls(_description, _example, _version, _other)

    @property
    def version(self):
        from asdf import versioning

        if self._version is None:
            return versioning.default_version

        version = self._version.lower().split("asdf-standard-")[1]
        return versioning.AsdfVersion(version)


class AsdfSchemaExampleItem(pytest.Item):
    @classmethod
    def from_parent(
        cls,
        parent,
        schema_path,
        example,
        example_index,
        ignore_unrecognized_tag=False,
        **kwargs,
    ):
        if hasattr(super(), "from_parent"):
            result = super().from_parent(parent, **kwargs)
        else:
            name = kwargs.pop("name")
            result = AsdfSchemaExampleItem(name, parent, **kwargs)

        result.filename = str(schema_path)
        result.example = SchemaExample.from_schema(example)
        result.ignore_unrecognized_tag = ignore_unrecognized_tag
        return result

    def runtest(self):
        import asdf
        from asdf.testing.helpers import yaml_to_asdf

        # warn inside test, we don't do this yet to allow time for downstream packages to adopt pytest-asdf-plugin
        # warnings.warn("pytest_asdf is deprecated, install pytest_asdf_plugin instead", DeprecationWarning)

        # check the example is valid
        buff = yaml_to_asdf("example: " + self.example.example.strip(), version=self.example.version)
        tagged_tree = asdf.util.load_yaml(buff, tagged=True)
        instance = asdf.AsdfFile(version=self.example.version)
        asdf.schema.validate(tagged_tree, instance, reading=True)

    def reportinfo(self):
        return self.fspath, 0, ""


def _parse_test_list(content):
    result = {}

    if isinstance(content, str):
        content = content.split("\n")

    for line in content:
        line_ = line.strip()
        if len(line_) > 0:
            parts = line_.split("::", 1)
            path_suffix = pathlib.Path(parts[0]).as_posix()

            name = "*" if len(parts) == 1 else parts[-1]

            if path_suffix not in result:
                result[path_suffix] = []

            result[path_suffix].append(name)

    return result


def pytest_collect_file(file_path, parent):
    if HAS_NEW_PLUGIN:
        return None
    if not (parent.config.getini("asdf_schema_tests_enabled") or parent.config.getoption("asdf_tests")):
        return None

    schema_roots = parent.config.getini("asdf_schema_root").split()
    if not schema_roots:
        return None

    skip_names = parent.config.getini("asdf_schema_skip_names")
    skip_examples = parent.config.getini("asdf_schema_skip_examples")
    validate_default = parent.config.getini("asdf_schema_validate_default")
    ignore_unrecognized_tag = parent.config.getini("asdf_schema_ignore_unrecognized_tag")

    skip_tests = _parse_test_list(parent.config.getini("asdf_schema_skip_tests"))
    xfail_tests = _parse_test_list(parent.config.getini("asdf_schema_xfail_tests"))

    schema_roots = [os.path.join(str(parent.config.rootpath), os.path.normpath(root)) for root in schema_roots]

    if file_path.suffix != ".yaml":
        return None

    for root in schema_roots:
        if str(file_path).startswith(root) and file_path.stem not in skip_names:
            posix_path = pathlib.Path(file_path).as_posix()
            schema_skip_tests = []
            for suffix, names in skip_tests.items():
                if posix_path.endswith(suffix):
                    schema_skip_tests.extend(names)
            schema_xfail_tests = []
            for suffix, names in xfail_tests.items():
                if posix_path.endswith(suffix):
                    schema_xfail_tests.extend(names)

            return AsdfSchemaFile.from_parent(
                parent,
                fspath=file_path,
                skip_examples=(file_path.stem in skip_examples),
                validate_default=validate_default,
                ignore_unrecognized_tag=ignore_unrecognized_tag,
                skip_tests=schema_skip_tests,
                xfail_tests=schema_xfail_tests,
            )

    return None
