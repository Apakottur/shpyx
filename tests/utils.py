"""
Shared test utilities.
"""

import platform

import shpyx

# Platform OS.
SYSTEM = platform.system()

# Utility constant for making tests compatible with Windows, where lines **sometimes** end with a carriage return, in
# addition to a line break.
SEP = "\r\n" if SYSTEM == "Windows" else "\n"


def verify_result(
    result: shpyx.ShellCmdResult,
    *,
    return_code: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> None:
    assert return_code == result.return_code
    assert stdout == result.stdout
    assert stderr == result.stderr
