import platform
import shlex
from enum import Enum

from shpyx._errors import ShpyxOSNotSupportedError


class _System(Enum):
    """The platform systems supported by shpyx, used for platform specific code."""

    LINUX = "Linux"
    DARWIN = "Darwin"
    WINDOWS = "Windows"


def _get_system() -> _System:
    """
    Get the current platform system.

    Raises:
        ShpyxOSNotSupportedError: The current system is not supported.
    """
    system = platform.system()
    try:
        return _System(system)
    except ValueError:
        raise ShpyxOSNotSupportedError(f"Unsupported system: {system}") from None


_SYSTEM = _get_system()


def _get_unix_raw_cmd(cmd_str: str) -> str:
    """
    Wrap a shell command with the `script` Unix utility, so that its output is captured as if written to a terminal.
    The typescript file is not needed (the output is read from the pipes), so it is discarded to `/dev/null`.

    Raises:
        ShpyxOSNotSupportedError: The `script` utility is not available on Windows.
    """
    match _SYSTEM:
        case _System.LINUX:
            # Old format: https://linux.die.net/man/1/script
            # New format: https://man7.org/linux/man-pages/man1/script.1.html
            return f"script --return --quiet --command {shlex.quote(cmd_str)} /dev/null"
        case _System.DARWIN:
            # MacOS format: https://keith.github.io/xcode-man-pages/script.1.html
            # The command is executed directly (not through a shell), so wrap it with `sh -c` to support shell logic.
            return f"script -q /dev/null /bin/sh -c {shlex.quote(cmd_str)}"
        case _System.WINDOWS:  # pragma: no branch, the match is exhaustive
            raise ShpyxOSNotSupportedError(f"Unsupported system: {_SYSTEM.value}")
