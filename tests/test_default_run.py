"""
Test the default runner, `shpyx.run`.
"""
import platform

import shpyx

_SYSTEM = platform.system()


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


def test_echo_as_list() -> None:
    if _SYSTEM == "Windows":
        result = shpyx.run(["echo", "1"])
        _verify_result(result, return_code=0, stdout="1\r\n", stderr="")
    else:
        result = shpyx.run(["echo", "1"])
        _verify_result(result, return_code=0, stdout="1\n", stderr="")


def test_echo_as_string() -> None:
    if _SYSTEM == "Windows":
        result = shpyx.run("echo 1")
        _verify_result(result, return_code=0, stdout="1\r\n", stderr="")
    else:
        result = shpyx.run("echo 1")
        _verify_result(result, return_code=0, stdout="1\n", stderr="")
