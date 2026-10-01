"""Script to convert Sphinx RST files to mkdocs markdown files.

Accepts one or more input files or directories and a single output directory.

# TODO
This script should not be in the final codebase.
It should be deleted before merging the PR.
"""

import importlib
import re
import subprocess
from pathlib import Path

import click

CURRENT_MOD_RE = re.compile(r'<div class="currentmodule">([^<]+)<\/div>\s*', flags=re.MULTILINE)
REFERENCE_RE = re.compile(r'<span class="title-ref">([^<]+)<\/span>', flags=re.MULTILINE)


def fix_references(file: str) -> str:
    """Fix API references."""
    # Find `currentmodule` statements
    current_mod = [(m[1].strip(), m.end()) for m in CURRENT_MOD_RE.finditer(file)]
    if not current_mod:
        # Without a currentmodule directive Sphinx still defaults to `asdf` (I think)
        current_mod = [("asdf", 0)]

    def sub_ref(m: re.Match) -> str:
        qualname: str = m[1].strip()
        name = qualname

        if qualname.startswith("~"):
            # Ref starting with ~ means that the link text should be just the last part of the path
            qualname = qualname[1:]
            _, _, name = qualname.rpartition(".")

        if qualname.endswith("()"):
            # Strip `()` from link target but leave in link text
            qualname = qualname[:-2]

        basemod, _, _ = qualname.partition(".")
        # If the root module of the ref can't be imported see if there's a valid prefix
        if not _can_import(basemod):
            for curmod, idx in reversed(current_mod):
                # Find most recent `currentmodule` directive before this ref
                if idx < m.start():
                    if _can_import(f"{curmod}.{basemod}"):
                        qualname = f"{curmod}.{qualname}"

                    break

        return f"[`{name}`][{qualname}]"

    file = REFERENCE_RE.sub(sub_ref, file)
    # Remove residual `currentmodule` statements
    return CURRENT_MOD_RE.sub("", file)


def _can_import(path: str) -> bool:
    try:
        _ = importlib.import_module(path)
    except ImportError:
        basemod, _, obj = path.rpartition(".")
        if not basemod:
            return False

        try:
            m = importlib.import_module(basemod)
            return hasattr(m, obj)
        except ImportError:
            return False
    else:
        return True


ADMONITION_RE = re.compile(r"> \[!([a-zA-Z]+)\]\s*((?:> ?[^\n]*\n)+)", flags=re.MULTILINE)


def fix_admonitions(file: str) -> str:
    """Convert admonitions to the format expected by mkdocs."""

    def sub_admonition(m: re.Match) -> str:
        kind: str = m[1]
        lines: str = m[2]
        block = re.sub(r"> ?", r"\t", lines)
        return f"!!! {kind.lower()}\n{block}"

    return ADMONITION_RE.sub(sub_admonition, file)


PYCON_FENCE_RE = re.compile(r"```[a-zA-Z ]*\n>>>", flags=re.MULTILINE)
PYCON_END_RE = re.compile(r"^((?:>>>|\.\.\.) .+?$\n)```", flags=re.MULTILINE)


def fix_pycon_blocks(file: str) -> str:
    # Find fenced code blocks containing `>>>` lines and mark them as `pycon`
    file = PYCON_FENCE_RE.sub("```pycon\n>>>", file)
    # Ensure pycon blocks have a final output line
    return PYCON_END_RE.sub("\g<1>\n```", file)


TITLE_RE = re.compile(r"^---\s+^title: (.+)\s^---", flags=re.MULTILINE)
HEADER_RE = re.compile(r"^(#+) \b", flags=re.MULTILINE)


def title_to_header(file: str) -> str:
    """Check if file has a `title` frontmatter entry.

    If so add it as a level 1 header and shift all other headers down a level
    """
    parts = TITLE_RE.split(file, maxsplit=1)
    if len(parts) > 1:
        file = f"# {parts[1]}" + HEADER_RE.sub("#\g<1> ", parts[2])
    return file


# List of transforms to apply to each file after RST->MD conversion
TRANSFORMS = [
    title_to_header,
    fix_references,
    fix_admonitions,
    fix_pycon_blocks,
]


def process_file(src: Path, dst: Path, dry_run: bool) -> None:
    print(f"{src} -> {dst}")
    if dry_run:
        return

    # Convert input from RST to markdown using pandoc
    # Github-flavored markdown seems to produce slightly better results
    subprocess.run(["pandoc", "-s", "--read=rst", "--write=gfm", "-o", str(dst), str(src)], check=True)  # noqa: S603, S607

    # Read file, apply transforms, then write back out
    txt = dst.read_text()
    for tfm in TRANSFORMS:
        txt = tfm(txt)
    dst.write_text(txt)


def expand_paths(src: Path):
    if src.is_dir():
        for path in src.rglob("*.rst"):
            yield (path, path.relative_to(src))
    else:
        yield (src, Path(src.name))


@click.command
@click.argument("sources", nargs=-1, type=click.Path(path_type=Path, exists=True))
@click.option("-o", "--out", type=click.Path(path_type=Path))
@click.option("--dry-run", is_flag=True)
def main(sources: tuple[Path], out: Path, dry_run: bool):
    out_is_dir = out.is_dir() or not (out.exists() or out.suffix)
    files = [s for src in sources for s in expand_paths(src)]

    if not out_is_dir:
        if len(files) > 1:
            msg = "Multiple input files specified but output is not a directory"
            raise RuntimeError(msg)

        process_file(files[0][0], out, dry_run)
        return

    for src, dst in files:
        dst = (out / dst).with_suffix(".md")
        process_file(src, dst, dry_run)


if __name__ == "__main__":
    main()
