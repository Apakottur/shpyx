"""
Test the command execution.
"""

from __future__ import annotations

import _thread
import codecs
import contextlib
import sys
import threading
import time
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import psutil
import pytest
import pytest_mock

import shpyx
from shpyx._execute import Process
from shpyx._output import OutputStream
from tests.utils import verify_result

if TYPE_CHECKING:
    from _typeshed import ReadableBuffer


class _SubprocessPopenIssue(Enum):
    CRASH = auto()
    STDOUT_PIPE_MISSING = auto()
    STDERR_PIPE_MISSING = auto()


class _NoStdoutProcess(Process):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.stdout = None


class _NoStderrProcess(Process):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.stderr = None


@pytest.mark.parametrize("issue", _SubprocessPopenIssue)
def test_fail_to_initialize_subprocess(mocker: pytest_mock.MockerFixture, issue: _SubprocessPopenIssue) -> None:
    match issue:
        case _SubprocessPopenIssue.CRASH:
            mocker.patch("shpyx._execute.Process", side_effect=OSError("Some SO error"))
        case _SubprocessPopenIssue.STDOUT_PIPE_MISSING:
            mocker.patch("shpyx._execute.Process", _NoStdoutProcess)
        case _SubprocessPopenIssue.STDERR_PIPE_MISSING:
            mocker.patch("shpyx._execute.Process", _NoStderrProcess)

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
    exit_spy = mocker.spy(Process, "__exit__")
    mocker.patch.object(OutputStream, "add", side_effect=KeyboardInterrupt)

    # A long-running command, with some output to trigger the interrupt.
    with pytest.raises(KeyboardInterrupt):
        shpyx.run([sys.executable, "-c", "import time; print(1, flush=True); time.sleep(30)"])

    proc: Process = exit_spy.call_args.args[0]
    assert proc.returncode is not None


# Print the PID of a process, then keep it running.
_PRINT_PID_AND_SLEEP = "import os, time; print(os.getpid(), flush=True); time.sleep(30)"


@pytest.mark.parametrize(
    "args",
    [
        # A shell pipeline, where the process printing the PID is a child of the shell.
        f'"{sys.executable}" -c "{_PRINT_PID_AND_SLEEP}" | "{sys.executable}" -c "import sys; '
        "[print(line, end='', flush=True) for line in sys.stdin]\"",
        # A process printing the PID of its own child, and waiting for it.
        [
            sys.executable,
            "-c",
            f"import subprocess, sys; subprocess.run([sys.executable, '-c', {_PRINT_PID_AND_SLEEP!r}])",
        ],
    ],
)
def test_descendants_killed_on_exception(args: str | list[str]) -> None:
    """An exception raised mid-run must kill the descendants of the child process as well, not only the child"""
    output = bytearray()

    class _FailingDecoder(codecs.IncrementalDecoder):
        # Collect the output, and fail once a full line (the PID of a grandchild process) arrived.

        def decode(self, input: ReadableBuffer, final: bool = False) -> str:  # noqa: A002, FBT001, FBT002, ARG002
            output.extend(bytes(input))
            if b"\n" in output:
                raise ValueError("Decoding failed")
            return ""

    with pytest.raises(ValueError, match="Decoding failed"):
        shpyx.run(args, decoder_factory=_FailingDecoder)

    # The grandchild is killed asynchronously, so wait for it to exit (raises on a timeout).
    with contextlib.suppress(psutil.NoSuchProcess):
        psutil.Process(int(output)).wait(timeout=10)


def test_interrupt_while_waiting_for_output() -> None:
    """A `KeyboardInterrupt` (e.g. CTRL-C) must stop a command promptly, even while no output arrives"""
    # Interrupt the main thread while it waits for the output of a silent long-running command.
    timer = threading.Timer(0.5, _thread.interrupt_main)
    timer.start()

    start = time.monotonic()
    with pytest.raises(KeyboardInterrupt):
        shpyx.run([sys.executable, "-c", "import time; time.sleep(30)"])

    assert time.monotonic() - start < 10


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
