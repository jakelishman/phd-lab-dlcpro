"""
Package for controlling the DLCPro laser controllers via a telnet connection.
The base connection is created by using the `LaserController` class, which in
turn provides a Python wrapper around the command and monitoring interfaces.

A lower-level interaction can be found in the `telnet` package, which provides
classes `telnet.Command` and `telnet.Monitor`, which can be used separately.
These are very basic wrappers around a telnet connection to the two interfaces,
and are not intended for general use.

The connections are logged, with loggers arranged in a hierarchy by module and
class names, using the standard `logging` Python library.  You can set the log
level for the whole package by doing
    import logging
    logging.getLogger(laser_controllers.__name__).setLevel("DEBUG")
(or whatever level you want), or you can use the standard methods to get finer
control over logging.
"""

try:
    import rx as _rx
    HAS_RX = True
except ImportError:
    _rx = None
    HAS_RX = False

from .errors import *
from .instrument import *

from . import errors as _errors
from . import instrument as _instrument
from . import telnet, parse

__all__ = _errors.__all__ + _instrument.__all__ + ['telnet', 'parse']
