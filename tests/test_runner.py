"""
Test the default runner, `shpyx.run`.
"""
import platform
import signal
import tempfile
from pathlib import Path

import pytest
import pytest_mock
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


def test_pipe() -> None:
    """Test the pipe operator of POSIX shells"""
    result = shpyx.run("seq 1 5 | grep '2'")
    _verify_result(result, return_code=0, stdout=f"2{_LINE_SEP}", stderr="")


def test_invalid_command() -> None:
    with pytest.raises(shpyx.ShpyxVerificationError, match="The command 'blabla' failed with return code"):
        shpyx.run("blabla")


def test_log_cmd(capfd: pytest.CaptureFixture[str]) -> None:
    shpyx.run("echo 1", log_cmd=True)

    cap_stdout, cap_stderr = capfd.readouterr()
    assert (cap_stdout, cap_stderr) == ("Running: echo 1\n", "")


def test_log_output(capfd: pytest.CaptureFixture[str]) -> None:
    shpyx.run("echo 1", log_output=True)

    cap_stdout, cap_stderr = capfd.readouterr()
    assert (cap_stdout, cap_stderr) == ("1\n", "")


def test_verify_stderr_disabled(capfd: pytest.CaptureFixture[str]) -> None:
    result = shpyx.run("echo 1 >&2", log_output=True, verify_stderr=False)
    _verify_result(result, return_code=0, stdout="", stderr=f"1{_LINE_SEP}")

    # The error message is logged in the STDOUT of the parent process.
    cap_stdout, cap_stderr = capfd.readouterr()
    assert (cap_stdout, cap_stderr) == ("1\n", "")


def test_verify_stderr_enabled(capfd: pytest.CaptureFixture[str]) -> None:
    cmd = "echo 1 >&2"
    with pytest.raises(
        shpyx.ShpyxVerificationError,
        match=f"The command '{cmd}' failed with return code 0.\n\nError output:\n1\n\nAll output:\n1\n",
    ):
        shpyx.run(cmd, log_output=True, verify_stderr=True)

    # The error message is logged in the STDOUT of the parent process.
    cap_stdout, cap_stderr = capfd.readouterr()
    assert (cap_stdout, cap_stderr) == ("1\n", "")


def test_verify_return_code() -> None:
    stderr_by_system = {
        "Linux": "/bin/sh: 1: blabla: not found\n",
        "Darwin": "/bin/sh: blabla: command not found\n",
        "Windows": "/bin/sh: 1: blabla: not found\n",
    }
    result = shpyx.run("blabla", verify_return_code=False)
    _verify_result(result, return_code=127, stdout="", stderr=stderr_by_system[_SYSTEM])


def test_env(capfd: pytest.CaptureFixture[str]) -> None:
    result = shpyx.run("echo $MY_VAR", env={"MY_VAR": "10"})
    _verify_result(result, return_code=0, stdout="10\n", stderr="")


def test_exec_dir(capfd: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        open(Path(temp_dir) / "test.txt", "w").write("avocado")

        result = shpyx.run("test -f test.txt", verify_return_code=False)
        _verify_result(result, return_code=1, stdout="", stderr="")

        result = shpyx.run("test -f test.txt", exec_dir=temp_dir, verify_return_code=False)
        _verify_result(result, return_code=0, stdout="", stderr="")

        result = shpyx.run("cat test.txt", exec_dir=temp_dir)
        _verify_result(result, return_code=0, stdout="avocado", stderr="")


def test_fail_to_initialize_subprocess(mocker: pytest_mock.MockerFixture) -> None:
    def _popen(*args: str, **kwargs: str) -> None:
        return None

    mocker.patch("shpyx.runner.subprocess.Popen", _popen)

    with pytest.raises(shpyx.ShpyxInternalError, match="Failed to initialize subprocess."):
        shpyx.run("echo 1")


def test_signal_names_enabled() -> None:
    signal_id = signal.Signals.SIGINT
    signal_name = signal.Signals(signal_id).name

    cmd = f"exit {signal_id}"
    with pytest.raises(shpyx.ShpyxVerificationError) as exc:
        shpyx.run(cmd)

    assert (
        exc.value.reason == f"The command '{cmd}' failed with return code {signal_id} ({signal_name})."
        f"\n\nError output:\n\nAll output:\n"
    )


def test_signal_names_disabled() -> None:
    signal_id = signal.Signals.SIGINT

    cmd = f"exit {signal_id}"
    with pytest.raises(shpyx.ShpyxVerificationError) as exc:
        runner = shpyx.Runner(use_signal_names=False)
        runner.run(cmd)

    assert (
        exc.value.reason == f"The command '{cmd}' failed with return code {signal_id}."
        f"\n\nError output:\n\nAll output:\n"
    )
