from __future__ import annotations

import contextlib
import os
import queue
import shlex
import subprocess
import sys
import threading
from typing import TYPE_CHECKING

import psutil

from shpyx._errors import ShpyxInternalError
from shpyx._output import OutputStream, read_stream
from shpyx._result import ShellCmdResult
from shpyx._system import get_unix_raw_cmd
from shpyx._verify import verify_result

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path
    from types import TracebackType

    from shpyx._output import DecoderFactory

# The maximal time (in seconds) to wait for output before checking for a pending interrupt (e.g. CTRL-C).
_INTERRUPT_CHECK_INTERVAL = 0.1


class Process(subprocess.Popen[bytes]):
    """Custom child process, with additional cleanup on exit."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        # On an exception (including `KeyboardInterrupt`), kill the child process instead of waiting for it to finish.
        # Its descendants are killed as well, since otherwise they are left running (e.g. the commands of a shell).
        if exc_type is not None:
            descendants = psutil.Process(self.pid).children(recursive=True)
            self.kill()
            for descendant in descendants:
                with contextlib.suppress(psutil.NoSuchProcess):
                    descendant.kill()
            self.wait()
        super().__exit__(exc_type, value, traceback)


def _log(msg: str) -> None:
    """
    Log a message to the standard output.
    """
    sys.stdout.write(msg)
    sys.stdout.flush()


def execute(
    args: str | Sequence[str | os.PathLike[str]],
    *,
    log_cmd: bool,
    log_output: bool,
    verify_return_code: bool,
    verify_stderr: bool,
    use_signal_names: bool,
    env: Mapping[str, str] | None,
    exec_dir: Path | str | None,
    unix_raw: bool,
    decoder_factory: DecoderFactory,
) -> ShellCmdResult:
    """
    Run a shell command, with a fully resolved configuration (see `Runner.run`).

    Raises:
        ShpyxOSNotSupportedError: The current OS is not supported for this operation.
        ShpyxInternalError: Internal error when executing the command.
        ShpyxVerificationError: If verification failed.
    """
    # The command as a single string, used for logging and in the result.
    if isinstance(args, str):
        cmd_str = args
    else:
        cmd_str = shlex.join(os.fspath(arg) for arg in args)

    if unix_raw:
        # The `script` utility receives the command as a single shell string, for both string and list arguments.
        args = get_unix_raw_cmd(cmd_str)

    # A string is run through an actual shell, to support shell logic like bash piping.
    # A list is run directly, with no need for a shell.
    use_shell = isinstance(args, str)

    # Log the command, if required.
    if log_cmd:
        _log(f"Running: {cmd_str}\n")

    # Build the command environment variables.
    cmd_env = os.environ.copy()
    if env is not None:
        # The provided env vars will take precedence over existing ones.
        cmd_env = {**cmd_env, **env}

    # Prepare the execution path.
    if exec_dir is not None:
        exec_dir = str(exec_dir)

    # Initialize the subprocess object.
    try:
        p = Process(
            args,
            shell=use_shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # Unbuffered, so that each read returns as soon as any data is available.
            bufsize=0,
            env=cmd_env,
            cwd=exec_dir,
        )
    except Exception as e:
        raise ShpyxInternalError("Failed to initialize subprocess (subprocess.Popen)") from e

    with p:
        # Verify that all the pipes were properly configured.
        if not p.stdout:
            raise ShpyxInternalError("Failed to initialize subprocess (stdout pipe)")
        if not p.stderr:
            raise ShpyxInternalError("Failed to initialize subprocess (stderr pipe)")

        # Initialize the result object.
        result = ShellCmdResult(cmd=cmd_str)

        # Create the output streams, each with a fresh decoder.
        all_output: list[str] = []
        stdout = OutputStream(decoder_factory(), all_output)
        stderr = OutputStream(decoder_factory(), all_output)

        # Read each output stream in its own thread, so that a command blocked on one full pipe can't deadlock the
        # read of the other. The chunks are consumed here in arrival order.
        chunks: queue.SimpleQueue[tuple[int, bytes]] = queue.SimpleQueue()
        for stream_id, stream in enumerate((p.stdout, p.stderr)):
            threading.Thread(target=read_stream, args=(stream, stream_id, chunks), daemon=True).start()

        streams = (stdout, stderr)
        open_streams = len(streams)
        while open_streams:
            # Wait with a timeout, since an indefinite wait can not be interrupted (e.g. by CTRL-C) on Windows.
            try:
                stream_id, chunk = chunks.get(timeout=_INTERRUPT_CHECK_INTERVAL)
            except queue.Empty:
                continue

            # An empty chunk marks the end of the stream, flushing any trailing incomplete bytes.
            final = not chunk
            if final:
                open_streams -= 1

            # Add the partial output to the result and log it, if needed.
            data = streams[stream_id].add(chunk, final=final)
            if data and log_output:
                _log(data)

    # Combine all the collected output parts.
    result.stdout = stdout.text()
    result.stderr = stderr.text()
    result.all_output = "".join(all_output)

    # Save return code (the process context manager waits for the process to exit).
    result.return_code = p.returncode

    # Verify that the command result is valid, based on the verification configuration.
    verify_result(
        result=result,
        verify_return_code=verify_return_code,
        verify_stderr=verify_stderr,
        use_signal_names=use_signal_names,
    )

    return result
