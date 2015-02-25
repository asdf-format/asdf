# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import atexit
import io
import os
import shutil
import tempfile
import textwrap

from docutils.parsers.rst import Directive
from docutils import nodes

from sphinx.util.nodes import set_source_info

from pyasdf import AsdfFile
from pyasdf.constants import ASDF_MAGIC, BLOCK_FLAG_STREAMED, BLOCK_FLAG_ENCODED
from pyasdf import versioning
from pyasdf import yamlutil

version_string = versioning.version_to_string(versioning.default_version)


TMPDIR = tempfile.mkdtemp()

def delete_tmpdir():
    shutil.rmtree(TMPDIR)


GLOBALS = {}
LOCALS = {}


FLAGS = {
    BLOCK_FLAG_STREAMED: 'BLOCK_FLAG_STREAMED',
    BLOCK_FLAG_ENCODED: 'BLOCK_FLAG_ENCODED'
}


class RunCodeDirective(Directive):
    has_content = True

    def run(self):
        code = textwrap.dedent('\n'.join(self.content))

        cwd = os.getcwd()
        os.chdir(TMPDIR)

        try:
            try:
                exec(code, GLOBALS, LOCALS)
            except:
                print(code)
                raise

            literal = nodes.literal_block(code, code)
            literal['language'] = 'python'
            set_source_info(self, literal)
        finally:
            os.chdir(cwd)
        return [literal]


class AsdfDirective(Directive):
    required_arguments = 1

    def run(self):
        filename = self.arguments[0]

        cwd = os.getcwd()
        os.chdir(TMPDIR)

        parts = []
        try:
            code = AsdfFile.read(filename, _get_yaml_content=True)
            code = '{0}{1}\n'.format(ASDF_MAGIC, version_string) + code.strip()
            literal = nodes.literal_block(code, code)
            literal['language'] = 'yaml'
            set_source_info(self, literal)
            parts.append(literal)

            ff = AsdfFile.read(filename)
            for i, block in enumerate(ff.blocks.internal_blocks):
                data = block.data.tostring().encode('hex')
                if len(data) > 40:
                    data = data[:40] + '...'
                allocated = block._allocated
                size = block._size
                memory_size = block._mem_size
                flags = block._flags

                if flags & BLOCK_FLAG_STREAMED:
                    allocated = size = memory_size = 0

                lines = []
                lines.append('BLOCK {0}:'.format(i))

                human_flags = []
                for key, val in FLAGS.items():
                    if flags & key:
                        human_flags.append(val)
                lines.append('    flags: {0}'.format(' | '.join(human_flags)))

                lines.append('    allocated_size: {0}'.format(allocated))
                lines.append('    used_size: {0}'.format(size))
                lines.append('    memory_size: {0}'.format(memory_size))

                if flags & BLOCK_FLAG_ENCODED:
                    buff = io.BytesIO()
                    encoding = yamlutil.dump(block.encoding, buff)
                    lines.append('    encoding: {0}'.format(buff.getvalue()[4:-5]))

                lines.append('    data: {0}'.format(data))

                code = '\n'.join(lines)

                literal = nodes.literal_block(code, code)
                literal['language'] = 'yaml'
                set_source_info(self, literal)
                parts.append(literal)

        finally:
            os.chdir(cwd)

        result = nodes.admonition()
        textnodes, messages = self.state.inline_text(filename, self.lineno)
        title = nodes.title(filename, '', *textnodes)
        result += title
        result.children.extend(parts)
        return [result]


def setup(app):
    app.add_directive('runcode', RunCodeDirective)
    app.add_directive('asdf', AsdfDirective)
    atexit.register(delete_tmpdir)
