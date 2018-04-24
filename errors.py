"""
Error classes and exceptions used by the package.  This module generally does
not need to be imported, because it is available in the root package namespace.
"""

import collections

__all__ = ['MachineError', 'ErrorCode']

class MachineError(Exception):
    """MachineError(code: int, message: str) -> MachineError

    Thrown when the machine indicates an error has occurred, but there is no
    callback registered to handle it."""
    def __init__(self, code, message):
        self.message = "{}: {}".format(code, message)

ErrorCode = collections.namedtuple('ErrorCode', ['code', 'message'])
