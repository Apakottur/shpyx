"""
Test the default runner, `shpyx.run`.
"""

from __future__ import annotations

import codecs
import platform
import signal
import subprocess
import tempfile
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tests.fake_proc import patch_fake_proc

if TYPE_CHECKING:
    from _typeshed import ReadableBuffer

import pytest
import pytest_mock

import src as shpyx

# Platform OS.
_SYSTEM = platform.system()

# Utility constant for making tests compatible with Windows, where lines **sometimes** end with a carriage return, in
# addition to a line break.
_SEP = "\r\n" if _SYSTEM == "Windows" else "\n"


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
    _verify_result(result, return_code=0, stdout=f"1{_SEP}", stderr="")


def test_echo_as_list() -> None:
    """Simple use case when input is a list"""
    result = shpyx.run(["echo", "1"])
    _verify_result(result, return_code=0, stdout="1\n", stderr="")


def test_pipe() -> None:
    """Test the pipe operator, making sure an actual shell is used for strings"""
    result = shpyx.run("seq 1 5 | grep '2'")
    _verify_result(result, return_code=0, stdout="2\n", stderr="")


def test_empty_command() -> None:
    result = shpyx.run("")
    _verify_result(result, return_code=0, stdout="", stderr="")


def test_invalid_command() -> None:
    stderr_by_platform = {
        "Windows": [
            "'banana' is not recognized as an internal or external command,\r\noperable program or batch file.\r\n",
        ],
        "Darwin": [
            "/bin/sh: banana: command not found\n",
        ],
        "Linux": [
            # '/bin/sh' is 'dash' (e.g. Debian/Ubuntu).
            "/bin/sh: 1: banana: not found\n",
            # '/bin/sh' is 'bash' (e.g. Arch/CachyOS).
            "/bin/sh: line 1: banana: command not found\n",
        ],
    }

    with pytest.raises(shpyx.ShpyxVerificationError) as exc:
        shpyx.run("banana")

    assert exc.value.result.stderr in stderr_by_platform[_SYSTEM]


def test_log_cmd(capfd: pytest.CaptureFixture[str]) -> None:
    shpyx.run("echo 1", log_cmd=True)

    cap_stdout, cap_stderr = capfd.readouterr()
    assert (cap_stdout, cap_stderr) == ("Running: echo 1\n", "")


def test_log_output(capfd: pytest.CaptureFixture[str]) -> None:
    shpyx.run("echo 1", log_output=True)

    cap_stdout, cap_stderr = capfd.readouterr()
    assert (cap_stdout, cap_stderr) == (f"1{_SEP}", "")


def test_verify_stderr_disabled(capfd: pytest.CaptureFixture[str]) -> None:
    """Verify that contents in STDERR don't trigger an exception when `verify_stderr` is False."""
    output_by_platform = {
        "Windows": "1 \r\n",
        "Darwin": "1\n",
        "Linux": "1\n",
    }

    result = shpyx.run("echo 1 1>&2", log_output=True, verify_stderr=False)
    _verify_result(result, return_code=0, stdout="", stderr=output_by_platform[_SYSTEM])

    # The error message is logged in the STDOUT of the parent process.
    cap_stdout, cap_stderr = capfd.readouterr()
    assert (cap_stdout, cap_stderr) == (output_by_platform[_SYSTEM], "")


def test_verify_stderr_enabled(capfd: pytest.CaptureFixture[str]) -> None:
    """Verify that contents in STDERR trigger an exception when `verify_stderr` is True."""
    output_by_platform = {
        "Windows": "1 \r\n",
        "Darwin": "1\n",
        "Linux": "1\n",
    }

    cmd = "echo 1 1>&2"
    with pytest.raises(shpyx.ShpyxVerificationError) as exc:
        shpyx.run(cmd, log_output=True, verify_stderr=True, use_signal_names=False)

    assert (
        exc.value.reason == f"The command '{cmd}' failed with return code 0.\n\n"
        f"Error output:\n{output_by_platform[_SYSTEM]}\n"
        f"All output:\n{output_by_platform[_SYSTEM]}"
    )

    # The error message is logged in the STDOUT of the parent process.
    cap_stdout, cap_stderr = capfd.readouterr()
    assert (cap_stdout, cap_stderr) == (output_by_platform[_SYSTEM], "")


def test_verify_return_code_disabled() -> None:
    """When disabled, a non-zero return code should not trigger an error"""
    result = shpyx.run("exit 33", verify_return_code=False)
    _verify_result(result, return_code=33, stdout="")


def test_env() -> None:
    """Set a custom environment variable in the subprocess"""
    cmd = "echo $MY_VAR"
    if _SYSTEM == "Windows":
        cmd = "echo %MY_VAR%"

    result = shpyx.run(cmd, env={"MY_VAR": "10"})
    _verify_result(result, return_code=0, stdout=f"10{_SEP}", stderr="")


def test_exec_dir() -> None:
    """Execute a command from a different directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        with open(Path(temp_dir) / "test.txt", "w") as test_file:
            test_file.write("avocado")

        result = shpyx.run("test -f test.txt", verify_return_code=False)
        _verify_result(result, return_code=1, stdout="", stderr="")

        result = shpyx.run("test -f test.txt", exec_dir=temp_dir, verify_return_code=False)
        _verify_result(result, return_code=0, stdout="", stderr="")

        result = shpyx.run("cat test.txt", exec_dir=temp_dir)
        _verify_result(result, return_code=0, stdout="avocado", stderr="")


class _SubprocessPopenIssue(Enum):
    CRASH = auto()
    STDOUT_PIPE_MISSING = auto()
    STDERR_PIPE_MISSING = auto()


@pytest.mark.parametrize("issue", _SubprocessPopenIssue)
def test_fail_to_initialize_subprocess(mocker: pytest_mock.MockerFixture, issue: _SubprocessPopenIssue) -> None:
    orig = subprocess.Popen

    def _popen(*args: Any, **kwargs: Any) -> Any:
        match issue:
            case _SubprocessPopenIssue.CRASH:
                raise OSError("Some SO error")
            case _SubprocessPopenIssue.STDOUT_PIPE_MISSING:
                p = orig(*args, **kwargs)
                p.stdout = None
                return p
            case _SubprocessPopenIssue.STDERR_PIPE_MISSING:
                p = orig(*args, **kwargs)
                p.stderr = None
                return p

    mocker.patch("src.runner.subprocess.Popen", _popen)

    with pytest.raises(shpyx.ShpyxInternalError) as exc:
        shpyx.run("echo 1")

    match issue:
        case _SubprocessPopenIssue.CRASH:
            assert str(exc.value) == "Failed to initialize subprocess (subprocess.Popen)"
        case _SubprocessPopenIssue.STDOUT_PIPE_MISSING:
            assert str(exc.value) == "Failed to initialize subprocess (stdout pipe)"
        case _SubprocessPopenIssue.STDERR_PIPE_MISSING:
            assert str(exc.value) == "Failed to initialize subprocess (stderr pipe)"


def test_signal_names_enabled() -> None:
    signal_id = signal.Signals.SIGINT
    signal_name: str = signal.Signals(signal_id).name

    cmd = f"exit {signal_id}"
    with pytest.raises(shpyx.ShpyxVerificationError) as exc:
        shpyx.run(cmd)

    assert (
        exc.value.reason == f"The command '{cmd}' failed with return code {signal_id} ({signal_name})."
        f"\n\nError output:\n\nAll output:\n"
    )


def test_signal_names_enabled_name_unknown() -> None:
    """Handle a single with an unknown name (not registered in the signal module)"""
    signal_id = 101

    cmd = f"exit {signal_id}"
    with pytest.raises(shpyx.ShpyxVerificationError) as exc:
        shpyx.run(cmd, use_signal_names=True)

    assert (
        exc.value.reason == f"The command '{cmd}' failed with return code {signal_id}."
        f"\n\nError output:\n\nAll output:\n"
    )


def test_signal_names_disabled() -> None:
    signal_id = signal.Signals.SIGINT

    cmd = f"exit {signal_id}"
    with pytest.raises(shpyx.ShpyxVerificationError) as exc:
        shpyx.Runner(use_signal_names=False).run(cmd)

    assert (
        exc.value.reason == f"The command '{cmd}' failed with return code {signal_id}."
        f"\n\nError output:\n\nAll output:\n"
    )


def test_unix_raw_enabled() -> None:
    """
    Test the `unix_raw` argument.
    """
    cur_dir = Path(__file__).parent

    # Verify that an indicative exception is raised when attempting to use `unix_raw` on Windows.
    if _SYSTEM == "Windows":
        with pytest.raises(shpyx.ShpyxOSNotSupportedError):
            shpyx.run("echo 1", unix_raw=True)

        return

    # Print a standard "Hello" to the terminal.
    output_by_platform = {
        "Darwin": "^D\x08\x08Hello\r\n",
        "Linux": "Hello\r\n",
    }
    result = shpyx.run(
        "./print_hello.py",
        exec_dir=cur_dir,
        unix_raw=True,
    )
    _verify_result(result, return_code=0, stdout=output_by_platform[_SYSTEM], stderr="")

    # Print a colorful "Hello" without using 'unix_raw'.
    output_by_platform = {
        "Darwin": "\x1b[6;30;42mHello\x1b[0m\n",
        "Linux": "\x1b[6;30;42mHello\x1b[0m\n",
    }
    result = shpyx.run(
        "./print_hello.py",
        exec_dir=cur_dir,
        env={"TEST_ENABLE_COLOR": "1"},
    )
    _verify_result(result, return_code=0, stdout=output_by_platform[_SYSTEM], stderr="")

    # Print a colorful "Hello" with 'unix_raw'.
    output_by_platform = {
        "Darwin": "^D\x08\x08\x1b[6;30;42mHello\x1b[0m\r\n",
        "Linux": "\x1b[6;30;42mHello\x1b[0m\r\n",
    }
    result = shpyx.run(
        "./print_hello.py",
        exec_dir=cur_dir,
        env={"TEST_ENABLE_COLOR": "1"},
        unix_raw=True,
    )
    _verify_result(result, return_code=0, stdout=output_by_platform[_SYSTEM], stderr="")

    # Run a failing command in unix_raw mode and verify the output object.
    stderr_by_platform = {
        "Darwin": "^D\x08\x08hi\r\n",
        "Linux": "hi\r\n",
    }
    result = shpyx.run(
        "echo 'hi' && exit 123",
        unix_raw=True,
        verify_return_code=False,
    )
    assert result.return_code == 123
    assert result.all_output == stderr_by_platform[_SYSTEM]


def test_output_decoding(mocker: pytest_mock.MockerFixture) -> None:
    """
    Decoding must gracefully handle two separate hazards in a single run:
      1. A valid multibyte UTF-8 character split across two output stream reads.
      2. A genuinely invalid UTF-8 byte in the output (e.g. binary/Latin-1 data).
    """
    # '€' is b"\xe2\x82\xac". Split it across two reads, then feed a lone invalid byte (b"\xff").
    patch_fake_proc(mocker, stdout_chunks=[b"\xe2\x82", b"\xac", b"\xff"], stderr_chunks=[])

    result = shpyx.run("dummy_cmd")
    assert result.stdout == "€�"
    assert result.stderr == ""


def test_output_decoding_custom_decoder(mocker: pytest_mock.MockerFixture) -> None:
    """
    Test the `decoder_factory` argument.
    """

    class _AppendADecoder(codecs.IncrementalDecoder):
        # Custom decoder adding 'a' to each byte.

        def decode(self, input: ReadableBuffer, final: bool = False) -> str:  # noqa: A002, FBT001, FBT002, ARG002
            return "".join(f"{byte:c}a" for byte in bytes(input))

    # 'hi' -> 'h','a','i','a'
    patch_fake_proc(mocker, stdout_chunks=[b"hi"], stderr_chunks=[])

    result = shpyx.run("dummy_cmd", decoder_factory=_AppendADecoder)
    assert result.stdout == "haia"
