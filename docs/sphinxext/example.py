# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import atexit
import io
import os
import shutil
import tempfile
import textwrap
import codecs

from docutils.parsers.rst import Directive
from docutils import nodes

from sphinx.util.nodes import set_source_info

from asdf import AsdfFile
from asdf.constants import ASDF_MAGIC, BLOCK_FLAG_STREAMED
from asdf import versioning, util

version_string = str(versioning.default_version)


TMPDIR = tempfile.mkdtemp()


def delete_tmpdir():
    shutil.rmtree(TMPDIR)

GLOBALS = {}

FLAGS = {
    BLOCK_FLAG_STREAMED: "BLOCK_FLAG_STREAMED"
}


class RunCodeDirective(Directive):
    has_content = True
    optional_arguments = 1

    def run(self):
        code = textwrap.dedent('\n'.join(self.content))

        cwd = os.getcwd()
        os.chdir(TMPDIR)

        try:
            try:
                exec(code, GLOBALS)
            except:
                print(code)
                raise

            literal = nodes.literal_block(code, code)
            literal['language'] = 'python'
            set_source_info(self, literal)
        finally:
            os.chdir(cwd)

        if 'hidden' not in self.arguments:
            return [literal]
        else:
            return []


class AsdfDirective(Directive):
    required_arguments = 1
    optional_arguments = 1

    def run(self):
        filename = self.arguments[0]

        cwd = os.getcwd()
        os.chdir(TMPDIR)

        parts = []
        try:
            ff = AsdfFile()
            code = AsdfFile._open_impl(ff, filename, _get_yaml_content=True)
            code = '{0} {1}\n'.format(ASDF_MAGIC, version_string) + code.strip().decode('utf-8')
            literal = nodes.literal_block(code, code)
            literal['language'] = 'yaml'
            set_source_info(self, literal)
            parts.append(literal)

            kwargs = dict()
            # Use the ignore_unrecognized_tag parameter as a proxy for both options
            kwargs['ignore_unrecognized_tag'] = 'ignore_unrecognized_tag' in self.arguments
            kwargs['ignore_missing_extensions'] = 'ignore_unrecognized_tag' in self.arguments

            with AsdfFile.open(filename, **kwargs) as ff:
                for i, block in enumerate(ff.blocks.internal_blocks):
                    data = codecs.encode(block.data.tostring(), 'hex')
                    if len(data) > 40:
                        data = data[:40] + '...'.encode()
                    allocated = block._allocated
                    size = block._size
                    data_size = block._data_size
                    flags = block._flags

                    if flags & BLOCK_FLAG_STREAMED:
                        allocated = size = data_size = 0

                    lines = []
                    lines.append('BLOCK {0}:'.format(i))

                    human_flags = []
                    for key, val in FLAGS.items():
                        if flags & key:
                            human_flags.append(val)
                    if len(human_flags):
                        lines.append('    flags: {0}'.format(' | '.join(human_flags)))
                    if block.input_compression:
                        lines.append('    compression: {0}'.format(block.input_compression))
                    lines.append('    allocated_size: {0}'.format(allocated))
                    lines.append('    used_size: {0}'.format(size))
                    lines.append('    data_size: {0}'.format(data_size))
                    lines.append('    data: {0}'.format(data))

                    code = '\n'.join(lines)

                    literal = nodes.literal_block(code, code)
                    literal['language'] = 'yaml'
                    set_source_info(self, literal)
                    parts.append(literal)

                internal_blocks = list(ff.blocks.internal_blocks)
                if (len(internal_blocks) and
                    internal_blocks[-1].array_storage != 'streamed'):
                    buff = io.BytesIO()
                    ff.blocks.write_block_index(buff, ff)
                    block_index = buff.getvalue().decode('utf-8')
                    literal = nodes.literal_block(block_index, block_index)
                    literal['language'] = 'yaml'
                    set_source_info(self, literal)
                    parts.append(literal)

        finally:
            os.chdir(cwd)

        result = nodes.admonition()
        textnodes, messages = self.state.inline_text(filename, self.lineno)
        title = nodes.title(filename, '', *textnodes)
        result += title
        result += parts
        return [result]


def setup(app):
    app.add_directive('runcode', RunCodeDirective)
    app.add_directive('asdf', AsdfDirective)
    atexit.register(delete_tmpdir)
