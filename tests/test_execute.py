"""
Test the command execution.
"""

from __future__ import annotations

import sys
import threading
from enum import Enum, auto
from typing import Any

import pytest
import pytest_mock

import shpyx
from shpyx._execute import _Process
from shpyx._output import _OutputStream
from tests.utils import verify_result


class _SubprocessPopenIssue(Enum):
    CRASH = auto()
    STDOUT_PIPE_MISSING = auto()
    STDERR_PIPE_MISSING = auto()


class _NoStdoutProcess(_Process):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.stdout = None


class _NoStderrProcess(_Process):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.stderr = None


@pytest.mark.parametrize("issue", _SubprocessPopenIssue)
def test_fail_to_initialize_subprocess(mocker: pytest_mock.MockerFixture, issue: _SubprocessPopenIssue) -> None:
    match issue:
        case _SubprocessPopenIssue.CRASH:
            mocker.patch("shpyx._execute._Process", side_effect=OSError("Some SO error"))
        case _SubprocessPopenIssue.STDOUT_PIPE_MISSING:
            mocker.patch("shpyx._execute._Process", _NoStdoutProcess)
        case _SubprocessPopenIssue.STDERR_PIPE_MISSING:
            mocker.patch("shpyx._execute._Process", _NoStderrProcess)

    with pytest.raises(shpyx.ShpyxInternalError) as exc:
        shpyx.run("echo 1")

    match issue:
        case _SubprocessPopenIssue.CRASH:
            assert str(exc.value) == "Failed to initialize subprocess (subprocess.Popen)"
        case _SubprocessPopenIssue.STDOUT_PIPE_MISSING:
            assert str(exc.value) == "Failed to initialize subprocess (stdout pipe)"
        case _SubprocessPopenIssue.STDERR_PIPE_MISSING:
            assert str(exc.value) == "Failed to initialize subprocess (stderr pipe)"


def test_child_killed_on_interrupt(mocker: pytest_mock.MockerFixture) -> None:
    """An exception raised mid-run (e.g. `KeyboardInterrupt`) must not leave an orphaned child process behind"""
    exit_spy = mocker.spy(_Process, "__exit__")
    mocker.patch.object(_OutputStream, "add", side_effect=KeyboardInterrupt)

    # A long-running command, with some output to trigger the interrupt.
    with pytest.raises(KeyboardInterrupt):
        shpyx.run([sys.executable, "-c", "import time; print(1, flush=True); time.sleep(30)"])

    proc: _Process = exit_spy.call_args.args[0]
    assert proc.returncode is not None


def test_large_stderr_before_stdout() -> None:
    """
    A command filling the stderr pipe before writing to (and closing) stdout must not deadlock.
    """
    size = 200_000
    code = f"import sys; sys.stderr.write('e' * {size}); sys.stderr.flush(); sys.stdout.write('o' * {size})"
    results: list[shpyx.ShellCmdResult] = []

    # Run in a thread, so that a deadlock fails the test instead of hanging it.
    thread = threading.Thread(target=lambda: results.append(shpyx.run([sys.executable, "-c", code])), daemon=True)
    thread.start()
    thread.join(timeout=60)
    assert not thread.is_alive(), "The command deadlocked"

    verify_result(results[0], stdout="o" * size, stderr="e" * size)
