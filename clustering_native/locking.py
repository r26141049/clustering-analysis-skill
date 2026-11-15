"""Serialize full local Session transactions, including read/validate/write.

Advisory OS locks protect cooperating local API/CLI processes. They do not
provide distributed storage locks, identity authentication or tamper resistance.
"""
from contextlib import contextmanager
from functools import wraps
import os
from .core import file_hash

@contextmanager
def session_lock(path):
    with open(path, 'a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            if handle.tell() == 0: handle.write(b'0'); handle.flush()
            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try: yield
        finally:
            if os.name == 'nt':
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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
