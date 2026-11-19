"""Serialize full local Session transactions, including read/validate/write.

Advisory OS locks protect cooperating local API/CLI processes. They do not
provide distributed storage locks, identity authentication or tamper resistance.
"""
from contextlib import contextmanager
from functools import wraps
import os
import time
from .core import file_hash

# A stalled sibling process must not block an entire Work interaction forever.
# This is a local advisory lock, not a distributed lock or authorization token.
LOCK_WAIT_SECONDS = 5.0


@contextmanager
def session_lock(path):
    with open(path, 'a+b') as handle:
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        if os.name == 'nt':
            import msvcrt
            if handle.seek(0, 2) == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            def try_lock():
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    return True
                except OSError:
                    return False
        else:
            import fcntl
            def try_lock():
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return True
                except BlockingIOError:
                    return False
        while not try_lock():
            if time.monotonic() >= deadline:
                raise TimeoutError('Session lock busy after 5s; do not re-submit approval blindly. Read gate_status and investigate active process.')
            time.sleep(min(.05, max(.001, deadline-time.monotonic())))
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def transaction(fn):
    @wraps(fn)
    def wrapped(self, *args, **kwargs):
        local = self._transaction_local
        if getattr(local, 'depth', 0):
            return fn(self, *args, **kwargs)
        with self._transaction_mutex:
            with session_lock(self.directory/'.session.lock'):
                local.depth=1
                try:
                    current=file_hash(self.directory/'session.json')
                    if getattr(self, '_disk_hash', current) != current:
                        self.__init__(self.directory)
                    return fn(self, *args, **kwargs)
                finally:
                    local.depth=0
                    self._disk_hash=file_hash(self.directory/'session.json')
    return wrapped
