import os
import tempfile
import sys
import errno


if os.name == 'nt': # pragma: no cover
    import random
    import time

    _rename = lambda src, dst: False
    _rename_atomic = lambda src, dst: False

    import ctypes

    _MOVEFILE_REPLACE_EXISTING = 0x1
    _MOVEFILE_WRITE_THROUGH = 0x8
    _MoveFileEx = ctypes.windll.kernel32.MoveFileExW

    def _rename(src, dst):
        if not isinstance(src, str):
            src = str(src, sys.getfilesystemencoding())
        if not isinstance(dst, str):
            dst = str(dst, sys.getfilesystemencoding())
        if _rename_atomic(src, dst):
            return True
        retry = 0
        rv = False
        while not rv and retry < 100:
            rv = _MoveFileEx(src, dst, _MOVEFILE_REPLACE_EXISTING |
                                       _MOVEFILE_WRITE_THROUGH)
            if not rv:
                time.sleep(0.001)
                retry += 1
        return rv

    # new in Vista and Windows Server 2008
    _CreateTransaction = ctypes.windll.ktmw32.CreateTransaction
    _CommitTransaction = ctypes.windll.ktmw32.CommitTransaction
    _MoveFileTransacted = ctypes.windll.kernel32.MoveFileTransactedW
    _CloseHandle = ctypes.windll.kernel32.CloseHandle

    def _rename_atomic(src, dst):
        ta = _CreateTransaction(None, 0, 0, 0, 0, 1000, 'Atomic rename')
        if ta == -1:
            return False
        try:
            retry = 0
            rv = False
            while not rv and retry < 100:
                rv = _MoveFileTransacted(src, dst, None, None,
                                         _MOVEFILE_REPLACE_EXISTING |
                                         _MOVEFILE_WRITE_THROUGH, ta)
                if rv:
                    rv = _CommitTransaction(ta)
                    break
                else:
                    time.sleep(0.001)
                    retry += 1
            return rv
        finally:
            _CloseHandle(ta)

    def atomic_rename(src, dst):
        # Try atomic or pseudo-atomic rename
        if _rename(src, dst):
            return
        # Fall back to "move away and replace"
        try:
            os.rename(src, dst)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            old = "%s-%08x" % (dst, random.randint(0, sys.maxsize))
            os.rename(dst, old)
            os.rename(src, dst)
            try:
                os.unlink(old)
            except Exception:
                pass
else:
    atomic_rename = os.rename


class _AtomicWFile(object):
    """Helper class for :func:`atomic_open`."""

    def __init__(self, f, tmp_filename, filename):
        self._f = f
        self._tmp_filename = tmp_filename
        self._filename = filename

    def __getattr__(self, attr):
        return getattr(self._f, attr)

    def __enter__(self):
        return self

    @property
    def name(self):
        return self._filename

    def close(self):
        if self._f.closed:
            return
        self._f.close()
        atomic_rename(self._tmp_filename, self._filename)

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            self.close()
        else:
            self._f.close()
            try:
                os.remove(self._tmp_filename)
            except OSError:
                pass

    def __repr__(self):
        return '<%s %s%r, mode %r>' % (
            self.__class__.__name__,
            self._f.closed and 'closed ' or '',
            self._filename,
            self._f.mode
        )


def atomic_open(filename, mode='w'):
    """Works like a regular `open()` but writes updates into a temporary
    file instead of the given file and moves it over when the file is
    closed.  The file returned behaves as if it was a regular Python
    """
    if mode in ('r', 'rb', 'r+', 'rb+', 'a', 'ab'):
        raise TypeError('Read or append modes don\'t work with atomic_open')
    f = tempfile.NamedTemporaryFile(mode, prefix='.asdf_tmp',
                                    dir=os.path.dirname(filename),
                                    delete=False)
    return _AtomicWFile(f, f.name, filename)
