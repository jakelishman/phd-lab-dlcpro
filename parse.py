"""
Functions for parsing the responses of the command interface and the
notifications of the monitoring interface into Python types, and vice-versa.

This module is typically internal, and need not be used by users of the library.
"""

from . import ErrorCode

__all__ = ['is_error', 'error', 'as_bytes', 'atom', 'response', 'notification']

def is_error(response):
    """is_error(response: bytes) -> bool

    Check whether a response is an error message."""
    return False

def error(response):
    """error(response: bytes) -> ErrorCode

    Parse an error response into an `ErrorCode` class with the code and the
    message in."""
    return ErrorCode(-1, "hello, world")

def as_bytes(value):
    """as_bytes(value: 'A) -> bytes

    Convert a Python type into an ASCII string which can be written to the
    machine.  Supported types are
        - bool (True -> b'#t', False -> b'#f')
        - str | bytes
        - int
        - float
        - tuple of any length, with each element a supported type"""
    if isinstance(value, tuple):
        return b'(' + b' '.join(map(as_bytes, value)) + b')'
    elif isinstance(value, bytes):
        return b'"' + value + b'"'
    elif isinstance(value, str):
        return b'"' + value.encode('ascii') + b'"'
    elif isinstance(value, bool):
        return b'#t' if value else b'#f'
    elif isinstance(value, int) or isinstance(value, float):
        return str(value).encode('ascii')
    raise ValueError("Unsupported type '{}' for value '{}'."\
                        .format(type(value), value))

_BOOLEAN = { b'#t': True, b'#f': False }

def atom(bytes_):
    """atom(bytes_: bytes) -> 'A

    Convert the machine representation of an atomic type into a Python type.
    Possible return values are of type
        - str
        - int
        - float
        - bool
    The return cannot be a tuple, and it is an error to attempt to parse a tuple
    using `atom`.  Use `response` instead.

    Raises:
    ValueError --
        The byte string cannot be exactly parsed into a supported type."""
    if bytes_[0] == ord('#') and bytes_ in _BOOLEAN:
        return _BOOLEAN[bytes_]
    elif bytes_[0] == ord('"') and bytes_[-1] == ord('"'):
        return bytes[1:-1].decode('utf-8')
    try:
        return int(bytes_)
    except ValueError:
        pass
    try:
        return float(bytes_)
    except ValueError:
        pass
    raise ValueError("Couldn't decode atom '" + bytes_.decode('utf-8') + "'.")

def _unmatched_exception(bytes_, pos):
    """Return the exception to be raised for an unmatched delimiter in a
    `bytes_` object at position `pos`."""
    return ValueError("Improper response '" + bytes_.decode('utf-8') + "'."
                      + "  Unmatched '{}' at position {}."\
                            .format(chr(bytes_[pos]), pos))

def _find_tuple_end(bytes_, start):
    """_find_tuple_end(bytes_: bytes, start: int) -> position: int

    Returns the index of the character one after the bracket which ends a
    particular tuple.  `start` should be the index in the byte string `bytes_`
    of the bracket which opens the tuple.

    The slice
        end = _find_tuple_end(bytes_, start)
        bytes_[start:end]
    is then the byte string of the tuple.

    Raises:
    ValueError -- If the tuple has no end bracket."""
    pos = start + 1
    open = 1
    while pos < len(bytes_):
        if bytes_[pos] == ord(')'):
            open = open - 1
            if open == 0:
                break
        elif bytes_[pos] == ord('('):
            open = open + 1
        elif bytes_[pos] == ord('"'):
            pos = bytes_.find(b'"', pos + 1)
            if pos < 0:
                break
        pos = pos + 1
    if pos < 0:
        raise _unmatched_exception(bytes_, start)
    return pos + 1

def _find_string_end(bytes_, start):
    """_find_string_end(bytes_: bytes, start: int) -> int

    Return the index of the character after the terminating '"' of a string in
    the bytes object `bytes_`, where the opening quote is at index `start`.
    Ignores the possibility of escaped string terminators, because the command
    manual doesn't mention an escape character.

    The slice
        end = _find_string_end(bytes_, start)
        bytes_[start:end]
    is then the string including its quotes.

    Raises:
    ValueError -- if there is no ending quote."""
    pos = bytes_.find(b'"', start + 1)
    if pos < 0:
        raise _unmatch_exception(bytes_, start)
    return pos + 1

def _response_recursive(bytes_):
    """_response_recursive(bytes_: bytes) -> tuple

    The recursive worker of `response()`.  Tokenises and parses the response
    recursively, returning a tuple at each level."""
    pos = end = 0
    out = []
    while pos < len(bytes_):
        if bytes_[pos] == ord('"'):
            end = _find_string_end(bytes_, pos)
            if end < 0:
                raise _unmatched_exception(bytes_, pos)
            out.append(bytes_[pos + 1:end - 1].decode('utf-8'))
        elif bytes_[pos] == ord('('):
            end = _find_tuple_end(bytes_, pos)
            if end < 0:
                raise _unmatched_exception(bytes_, pos)
            out.append(_response_recursive(bytes_[pos + 1:end - 1]))
        else:
            end = bytes_.find(b' ', pos + 1)
            end = len(bytes_) if end < 0 else end
            out.append(atom(bytes_[pos:end]))
        pos = end + 1
    return tuple(out)

def response(bytes_):
    """response(bytes_: bytes) -> 'A

    Parse the response of the machine into a Python type recursively.  The
    output type may be one of
        - bool
        - str | bytes
        - int
        - float
        - tuple of any length, with each element a supported type
    or the error state
        - ErrorCode.

    Raises:
    ValueError -- if the machine response was malformed in some manner."""
    if is_error(bytes_):
        return error(bytes)
    out =  _response_recursive(bytes_)
    if len(out) != 1:
        raise ValueError("Improper response '" + bytes_.decode('utf-8') + "'."
                         + "  Responses cannot contain spaces without being"
                         + " inside a tuple.")
    return out[0]
