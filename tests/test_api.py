"""
Test the public API, `shpyx.run` and `shpyx.Runner`.
"""

from __future__ import annotations

import os
import shlex
import sys
import tempfile
from pathlib import Path
from types import MappingProxyType

import pytest

import shpyx
from tests.utils import SEP, SYSTEM, verify_result


def test_echo_as_string() -> None:
    """Simple use case when input is a string"""
    result = shpyx.run("echo 1")
    verify_result(result, return_code=0, stdout=f"1{SEP}", stderr="")


def test_echo_as_list() -> None:
    """Simple use case when input is a list"""
    result = shpyx.run(["echo", "1"])
    verify_result(result, return_code=0, stdout="1\n", stderr="")


def test_args_sequence_with_paths() -> None:
    """Arguments can be any sequence of strings and paths"""
    args = (Path(sys.executable), "-c", "print(1)")
    result = shpyx.run(args)
    verify_result(result, return_code=0, stdout=f"1{SEP}", stderr="")
    assert result.cmd == shlex.join([os.fspath(args[0]), "-c", "print(1)"])


def test_list_cmd_display() -> None:
    """The displayed command of list arguments is shell-quoted"""
    assert shpyx.run(["echo", "a b"]).cmd == "echo 'a b'"


def test_pipe() -> None:
    """Test the pipe operator, making sure an actual shell is used for strings"""
    result = shpyx.run("seq 1 5 | grep '2'")
    verify_result(result, return_code=0, stdout="2\n", stderr="")


def test_empty_command() -> None:
    result = shpyx.run("")
    verify_result(result, return_code=0, stdout="", stderr="")


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

    assert exc.value.result.stderr in stderr_by_platform[SYSTEM]


def test_log_cmd(capfd: pytest.CaptureFixture[str]) -> None:
    shpyx.run("echo 1", log_cmd=True)

    cap_stdout, cap_stderr = capfd.readouterr()
    assert (cap_stdout, cap_stderr) == ("Running: echo 1\n", "")


def test_log_output(capfd: pytest.CaptureFixture[str]) -> None:
    shpyx.run("echo 1", log_output=True)

    cap_stdout, cap_stderr = capfd.readouterr()
    assert (cap_stdout, cap_stderr) == (f"1{SEP}", "")


def test_env() -> None:
    """Set a custom environment variable in the subprocess"""
    cmd = "echo $MY_VAR"
    if SYSTEM == "Windows":
        cmd = "echo %MY_VAR%"

    result = shpyx.run(cmd, env={"MY_VAR": "10"})
    verify_result(result, return_code=0, stdout=f"10{SEP}", stderr="")

    # Any mapping is supported.
    result = shpyx.run(cmd, env=MappingProxyType({"MY_VAR": "20"}))
    verify_result(result, return_code=0, stdout=f"20{SEP}", stderr="")


def test_exec_dir() -> None:
    """Execute a command from a different directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        with open(Path(temp_dir) / "test.txt", "w") as test_file:
            test_file.write("avocado")

        result = shpyx.run("test -f test.txt", verify_return_code=False)
        verify_result(result, return_code=1, stdout="", stderr="")

        result = shpyx.run("test -f test.txt", exec_dir=temp_dir, verify_return_code=False)
        verify_result(result, return_code=0, stdout="", stderr="")

        result = shpyx.run("cat test.txt", exec_dir=temp_dir)
        verify_result(result, return_code=0, stdout="avocado", stderr="")


def test_unix_raw_enabled() -> None:
    """
    Test the `unix_raw` argument.
    """
    cur_dir = Path(__file__).parent

    # Verify that an indicative exception is raised when attempting to use `unix_raw` on Windows.
    if SYSTEM == "Windows":
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
    verify_result(result, return_code=0, stdout=output_by_platform[SYSTEM], stderr="")

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
    verify_result(result, return_code=0, stdout=output_by_platform[SYSTEM], stderr="")

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
    verify_result(result, return_code=0, stdout=output_by_platform[SYSTEM], stderr="")

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
    assert result.all_output == stderr_by_platform[SYSTEM]

    # List arguments are supported as well.
    output_by_platform = {
        "Darwin": "^D\x08\x08a b\r\n",
        "Linux": "a b\r\n",
    }
    result = shpyx.run(["echo", "a b"], unix_raw=True)
    verify_result(result, return_code=0, stdout=output_by_platform[SYSTEM], stderr="")
