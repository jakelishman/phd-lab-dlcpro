"""
Low-level wrapper around telnet connections to the laser controllers for both
the command and the monitoring interfaces.  The monitoring interface is not
available if the `rx` package is not found (it can be installed via pip).

This package should not typically be necessary, as the root package provides the
`Command` and `Monitor` classses which give a higher-level interface to these
classes.
"""

from telnetlib import Telnet
from . import _rx, HAS_RX
import logging

__all__ = ['Command']
if HAS_RX:
    import rx
    __all__.append('Monitor')

DO_CMD = b'exec'
PROMPT = b'> '
QUERY_CMD = b'param-ref'
QUIT_CMD = b'quit'
SET_CMD = b'param-set!'
NEW_LINE = b'\r\n'

class Command:
    def __init__(self, ip_address, command_port=1998, timeout=None):
        self.logger_name = __name__ + ":" + ip_address + ":" + str(command_port)
        self.log = logging.getLogger(self.logger_name)
        self.closed = True
        try:
            if timeout:
                self.__connection = Telnet(ip_address, command_port, timeout)
            else:
                self.__connection = Telnet(ip_address, command_port)
            received = self.__connection.read_until(PROMPT).rstrip(PROMPT)
            self.log.debug("Received login message: " +received.decode('utf-8'))
            self.closed = False
        except ConnectionError as exc:
            self.log.error("Failed to make connection: " + str(exc))
            raise
        except TimeoutError:
            self.log.error("Connection operation timed out.")
            raise

    def __send(self, *parts):
        message = b"(" + b" ".join(parts) + b")\n"
        if self.closed:
            self.log.error("Connection closed, can't send message: "
                           + message.decode('utf-8')[:-1])
            raise ConnectionError("Connection is not active.")
        self.log.debug("Sending message: " + message.decode('utf-8')[:-1])
        self.__connection.write(message)

    def __receive(self):
        if self.closed:
            self.log.error("Connection closed, can't receive message: "
                           + message.decode('utf-8')[:-1])
            raise ConnectionError("Connection is not open.")
        received = self.__connection.read_until(PROMPT).rstrip(NEW_LINE+PROMPT)
        self.log.debug("Received response: " + received.decode('utf-8'))
        return b"".join(received.split(NEW_LINE)[1:]).rstrip(NEW_LINE)

    def do(self, command, *args):
        self.__send(DO_CMD, b"'" + command, *args)
        return self.__receive()

    def set(self, parameter, value):
        self.__send(SET_CMD, b"'" + parameter, value)
        return self.__receive()

    def query(self, parameter):
        self.__send(QUERY_CMD, b"'" + parameter)
        return self.__receive()

    def close(self):
        if self.closed:
            return
        self.log.debug("Closing connection.")
        self.__send(QUIT_CMD)
        self.closed = True

    def __enter__(self):
        """Returns the class instance, so it can be used as a
        `ContextManager`."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Safely closes the connections at the end of the context, and passes
        on any exceptions encountered during the closing."""
        self.close()
        return False

    def __del__(self):
        self.close()

if HAS_RX:
    class Monitor:
        def __init__(self, *args, **kwargs):
            self.all = None

        def close(self):
            return

        def add(self, parameter, interval=25, threshold=None):
            print(parameter, type(parameter))

        def remove(self, parameter):
            print(parameter)

        def remove_all(self):
            return

        def __enter__(self):
            """Returns the class instance, so it can be used as a
            `ContextManager`."""
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            """Safely closes the connections at the end of the context, and passes
            on any exceptions encountered during the closing."""
            self.close()
            return False

        def __del__(self):
            self.close()
