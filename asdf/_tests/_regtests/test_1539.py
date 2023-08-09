import io

import pytest

import asdf


@pytest.mark.xfail(reason="Fix will require more major changes to generic_io")
def test_invalid_seek_and_read_from_closed_memoryio():
    """
    Seek and read from closed MemoryIO

    https://github.com/asdf-format/asdf/issues/1539
    """
    b = io.BytesIO()
    b.write(b"\0" * 10)
    b.seek(0)
    f = asdf.generic_io.get_file(b)
    f.close()
    with pytest.raises(IOError, match="I/O operation on closed file."):
        f.read_into_array(10)
    assert b.tell() == 0
