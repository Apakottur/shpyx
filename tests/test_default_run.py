"""
Test the default runner, `shpyx.run`.
"""
import shpyx


def _verify_result(result: shpyx.ShellCmdResult, *, return_code: int = 0, stdout: str = "", stderr: str = ""):
    assert return_code == result.return_code
    assert stdout == result.stdout
    assert stderr == result.stderr


def test_echo():
    result = shpyx.run("echo 1")
    _verify_result(result, return_code=0, stdout="1\n", stderr="")
