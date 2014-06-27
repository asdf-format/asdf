# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import atexit
import os
import shutil
import sys
import tempfile
import textwrap

from docutils.parsers.rst import Directive
from docutils import nodes

from sphinx.util.nodes import set_source_info

from pyfinf import FinfFile
from pyfinf.constants import BLOCK_MAGIC


TMPDIR = tempfile.mkdtemp()

def delete_tmpdir():
    shutil.rmtree(TMPDIR)


BLOCK_DISPLAY = """
BLOCK {0}:
    flags: 0x{1:x}
    allocated: {2}
    size: {3}
    data: {4}
"""


GLOBALS = {}
LOCALS = {}


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


class FinfDirective(Directive):
    required_arguments = 1

    def run(self):
        filename = self.arguments[0]

        cwd = os.getcwd()
        os.chdir(TMPDIR)

        parts = []
        try:
            code = FinfFile.read(filename, _get_yaml_content=True)
            if len(code.strip()):
                literal = nodes.literal_block(code, code)
                literal['language'] = 'yaml'
                set_source_info(self, literal)
                parts.append(literal)

            ff = FinfFile.read(filename)
            for i, block in enumerate(ff.blocks.internal_blocks):
                data = block.data.tostring().encode('hex')
                if len(data) > 40:
                    data = data[:40] + '...'
                allocated = block._allocated
                size = block._size
                flags = block._flags
                if flags:
                    allocated = 0
                    size = 0
                code = BLOCK_DISPLAY.format(i, flags, allocated, size, data)
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
    app.add_directive('finf', FinfDirective)
    atexit.register(delete_tmpdir)
