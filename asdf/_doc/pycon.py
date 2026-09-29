"""Code block handlers for pycon code blocks."""

import re

DOCTEST_FLAG_RE = re.compile(r"(\s*#\s*doctest:.+)$", re.MULTILINE)


def strip_doctest_flags(src, language, css_class, options, md, **kwargs):
    """Strip doctest flags (`# doctest: +SKIP`) from rendered `pycon` codeblocks."""
    src = DOCTEST_FLAG_RE.sub("", src)
    return md.preprocessors["fenced_code_block"].extension.superfences[0]["formatter"](
        src=src, class_name="class_name", language=language, md=md, options=options, **kwargs
    )
