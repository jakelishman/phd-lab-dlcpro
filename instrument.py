"""
Provides the `Command` class for interacting with the instrument at a higher
level than the underlying Scheme-over-telnet, using Python types.

If the `rx` module is available, then this also provides the `Monitor` class
which is a high-level wrapper around the monitoring interface, using ReactiveX
`Observable` types.
"""

from . import telnet, parse, MachineError, ErrorCode
from . import _rx, HAS_RX
import functools

__all__ = ['Command', 'canonicalise']
if HAS_RX:
    __all__.append('Monitor')

def canonicalise(parameter):
    """Convert a string or byte string of a machine parameter into a canonical
    form, so it can safely be used for comparisons sent to the machine.

    The canonical form is a byte string with no padding spaces, and any trailing
    colons removed.

    Arguments:
    parameter: str | byte str -- the ASCII parameter string

    Returns:
    byte str -- the canonicalised form."""
    if isinstance(parameter, str):
        parameter = parameter.encode('ascii')
    elif not isinstance(parameter, bytes):
        raise ValueError("Coud not encode {} as an ASCII string."\
                         .format(parameter))
    return parameter.strip().rstrip(b":")

def canonical(function):
    """Decorator which converts the first argument of an instance method (so the
    second actual argument, the first after `self`) to canonical form for the
    machine.  This means stripping additional spacing and colons and converting
    to a byte string."""
    @functools.wraps(function)
    def inner(self, parameter, *args, **kwargs):
        return function(self, canonicalise(parameter), *args, **kwargs)
    return inner

class Command:
    """A ContextManager for communicating with the laser controller - this can
    be used in a `with` statement.  This provides a higher-level interface to
    the laser controller than the `telnet` command prompts, via the methods
    attached to this class.

    This command interface is accessed via the `do`, `set` and `query` methods
    for modifying and reading parameters in the controller."""
    def __init__(self, ip_address, command_port=1998, error_callback=None):
        """Open the connection to the laser controller.  You should hear it make
        some noise when the command port is connected.

        Arguments:
        ip_address: str -- The IP address of the machine to connect to.
        command_port: int --
            The port number of the command interface.  The machines default to
            1998."""
        self.__command = telnet.Command(ip_address, command_port)
        self.__error_callback = error_callback
        self.closed = False

    def close(self):
        """Close the underlying telnet connections to the laser controller
        gracefully."""
        if not self.closed:
            self.__command.close()
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

    def __handle_error(self, response, callback):
        """Decide what to do with an error code, whether that is calling a
        pre-defined callback function or raising a `MachineError`."""
        code, message = parse.error(response)
        if callback:
            return callback(code, message)
        elif self.error_callback:
            return self.__error_callback(code, message)
        else:
            raise MachineError(code, message)

    @canonical
    def set(self, parameter, value, error_callback=None):
        """set(parameter: byte str, value: byte str) -> None

        Set the parameter `parameter` to the value `value`.  If an error is
        received in response and `error_callback` is given, then pass execution
        to that function to handle the error.  Otherwise, raise an exception.

        Arguments:
        parameter: byte str | str --
            The parameter to set on the machine.  If given as a `str`, it must
            contain only ASCII characters.
        value: 'A --
            The value to set the parameter too.  This should be of the same type
            expected by the command or an instrument error will likely occur.
        error_callback: code: int, msg: str -> 'B --
            The function which will be called instead of raising an exception if
            an error state is return.  The first argument if the error code, and
            the second argument is the error message received.  This takes
            precedence over `LaserController.error_callback`.

        Returns:
        None -- If everything was successful.
        'B --
            The return value of the custom error callback if one was defined,
            and an error occurred.

        Raises:
        MachineError --
            If an error is encountered and neither the per-function error
            callback nor the class global error callback are defined."""
        response = self.__command.set(parameter, parse.as_bytes(value))
        if isinstance(response, ErrorCode):
            return self.__handle_error(response, error_callback)
        else:
            return None

    @canonical
    def query(self, parameter, error_callback=None):
        """query(parameter: str) -> response: 'A

        Query the command connection for the value of a parameter.  This returns
        the parsed response from the machine.

        Arguments:
        parameter: str | byte str --
            The parameter to query the value of.  If given as a `str`, it must
            contain only ASCII characters.
        error_callback: code: int, msg: str -> 'B --
            The function which will be called instead of raising an exception if
            an error state is return.  The first argument if the error code, and
            the second argument is the error message received.  This takes
            precedence over `LaserController.error_callback`.

        Returns:
        'A -- The response to the query, if it was successful.
        'B -- The result of the error callback, if unsuccessful.

        Raises:
        MachineError --
            If an error is encountered and neither the per-function error
            callback nor the class global error callback are defined."""
        out = parse.response(self.__command.query(parameter))
        if isinstance(out, ErrorCode):
            return self.__handle_error(out, error_callback)
        else:
            return out

    @canonical
    def do(self, command, *args, error_callback=None):
        response = self.__command.do(command, *map(parse.as_bytes, args))
        out = parse.response(response)
        if isinstance(out, ErrorCode):
            return self.__handle_error(response, error_callback)
        return (None if out == () else out)

if HAS_RX:
    class Monitor:
        """A ContextManager for communicating with the laser controller - this
        can be used in a `with` statement.  This provides a higher-level
        interface to the laser controller than the `telnet` command prompts, via
        the methods attached to this class.

        The monitoring interface can be accessed via the `begin_monitoring`,
        `monitor`, `stop_monitoring` and `stop_monitoring_all` methods, and the
        `monitor_all` property, which all expose or work with ReactiveX
        `Observable` types, accessible through the `rx` module available on pip.
        """
        def __init__(self, ip_address, monitor_port=1999, error_callback=None):
            self.__monitor = telnet.Monitor(ip_address, monitor_port)
            self.__monitors = {}
            self.monitor_all = self.__monitor.all
            self.__error_callback = error_callback
            self.closed = False

        def close(self):
            """Close the underlying telnet connections to the laser controller
            gracefully."""
            if not self.closed:
                self.__monitor.close()
                self.closed = True

        @canonical
        def is_monitoring(self, parameter):
            """is_monitoring(paramter: str) -> bool

            Return True if the machine is already set to monitor a particular
            parameter.  The relevant Observable can then be obtained with
            `LaserController.monitor(parameter)`.

            Arguments:
            parameter: byte str | str --
                The parameter to check for monitoring.  If given as a `str`, it
                must contain only ASCII characters.

            Returns:
            bool -- Whether or not we're monitoring it already."""
            return parameter in self.__monitors

        @canonical
        def begin_monitoring(self, parameter, interval=5, threshold=None):
            """Start monitoring a certain parameter on the controller at a
            certain interval.  Returns an `Observable` which emits every
            received change (it will not emit every `interval` if there has been
            no change).

            Arguments:
            parameter: str | byte str -- The parameter to monitor.
            interval: int in ms -- The frequency with which to poll for changes.
            threshold: 'A --
                The change in value required to trigger an event.  This should
                be of the same type as the parameter being monitored.  Events
                will only be triggered on the `Observable` if the change from
                the previous value exceeds this threshold.

            Returns:
            Observable<'A> --
                An `Observable` which emits the value of `parameter` on the
                machine at most every `interval` milliseconds, but only when it
                has changed.

            Raises:
            ValueError --
                If we're already monitoring the parameter (use
                `LaserController.monitor()` instead)."""
            if not self.is_monitoring(parameter):
                obs = self.__monitor.add(parameter, interval, threshold)
                self.__monitors[parameter] = obs, interval, threshold
                return obs
            else:
                raise ValueError(
                    "Already monitoring parameter " + parameter + ".")

        @canonical
        def monitor(self, parameter):
            """monitor(parameter: str) -> Observable<'A>

            Get the `Observable` for a parameter that is already being monitored
            by the machine (i.e. `LaserController.begin_monitoring(parameter)`
            has been called already).

            Arguments:
            parameter: str | byte str --
                The parameter to get the `Observable` for.  If passed as a
                `str`, it should contain only ASCII characters.

            Returns:
            Observable<'A> --
                The same `Observable` as was returned by the initial call to
                `LaserController.begin_monitoring()`.

            Raises:
            ValueError -- If we're not monitoring `parameter`."""
            if self.is_monitoring(parameter):
                return self.__monitors[parameter][0]
            else:
                raise ValueError("Not monitoring parameter " + parameter + ".")

        @canonical
        def stop_monitoring(self, parameter):
            """stop_monitoring(parameter: str) -> None

            Stop the machine from monitoring `parameter`.  This will also cause
            the relevant `Observable` to trigger the `on_completed` methods of
            its subscribers.

            Arguments:
            parameter: str | byte str --
                The parameter to stop monitoring.  If given as a `str`, it must
                contain only ASCII characters.

            Raises:
            ValueError -- If we're not monitoring `parameter`."""
            if self.is_monitoring(parameter):
                self.__monitor.remove(parameter)
                self.__monitors.pop(parameter, None)
            else:
                raise ValueError("Not monitoring parameter " + parameter + ".")

        def stop_monitoring_all(self):
            """stop_monitoring_all() -> None

            Stop monitoring everything on the machine.  This will trigger the
            `on_completed` call for every `Observable` that has been created
            already, except the `LaserController.monitor_all` one."""
            self.__monitor.remove_all()
            self.__monitors.clear()
