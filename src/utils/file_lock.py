"""Exclusive locks for append-only files on Windows and Unix."""
from contextlib import contextmanager
import errno
import os
import time


@contextmanager
def exclusive_file_lock(stream):
    """Keep buffered appends protected until flushed, including on failure."""
    if os.name == "nt":
        import msvcrt

        # Every writer locks the same byte, even when the file is still empty.
        stream.seek(0)
        while True:
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                time.sleep(0.05)
        try:
            yield
        finally:
            try:
                stream.flush()
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            try:
                stream.flush()
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
