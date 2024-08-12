from pathlib import Path

import asdf

TEST_DATA_DIRECTORY = Path(__file__).parent / "data"


def test_no_junk():
    asdf.open(TEST_DATA_DIRECTORY / "no_junk.asdf")


def test_junk_before_blocks():
    asdf.open(TEST_DATA_DIRECTORY / "junk_before_blocks.asdf")


def test_junk_after_blocks():
    asdf.open(TEST_DATA_DIRECTORY / "junk_after_blocks.asdf")
