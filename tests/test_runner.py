"""
Test the default runner, `shpyx.run`.
"""
import platform

import pytest
import shpyx

_SYSTEM = platform.system()

# The line separator is different between OSs.
_LINE_SEP = "\r\n" if _SYSTEM == "Windows" else "\n"


def _verify_result(
    result: shpyx.ShellCmdResult,
    *,
    return_code: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> None:
    assert return_code == result.return_code
    assert stdout == result.stdout
    assert stderr == result.stderr


def test_echo_as_string() -> None:
    """Simple use case when input is a string"""
    result = shpyx.run("echo 1")
    _verify_result(result, return_code=0, stdout=f"1{_LINE_SEP}", stderr="")


def test_echo_as_list() -> None:
    """Simple use case when input is a list"""
    result = shpyx.run(["echo", "1"])
    _verify_result(result, return_code=0, stdout=f"1{_LINE_SEP}", stderr="")


@pytest.mark.skipif(_SYSTEM == "Windows")
def test_sh_pipe() -> None:
    """Test the pipe operator of POSIX shells"""
    result = shpyx.run("seq 1 5 | grep '2'")
    _verify_result(result, return_code=0, stdout=f"2{_LINE_SEP}", stderr="")
