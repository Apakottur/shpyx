from __future__ import annotations

import codecs
import os
import platform
import queue
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from typing import IO, TYPE_CHECKING

from shpyx._errors import ShpyxInternalError, ShpyxOSNotSupportedError, ShpyxVerificationError
from shpyx._result import ShellCmdResult

if TYPE_CHECKING:
    from pathlib import Path

"""The platform system (Linux/Darwin/Windows/Java) is used for platform specific code"""
_SYSTEM = platform.system()

# The maximal number of bytes to read from a command output stream at once.
_READ_SIZE = 64 * 1024


# A callable that returns a fresh incremental decoder for a single command output stream.
_DecoderFactory = Callable[[], codecs.IncrementalDecoder]


def _default_decoder_factory() -> codecs.IncrementalDecoder:
    """
    Get the default output decoder factory:
        1. Decodes incrementally, so a valid multibyte character split across two reads (which are not aligned to
        character boundaries) is held until the next read completes it, rather than raising.
        2. Uses UTF-8.
        3. Replaces genuinely invalid bytes (e.g. binary data) with the Unicode replacement character instead of raising.
    """
    return codecs.getincrementaldecoder("utf-8")(errors="replace")


def _is_action_required(*, user: bool | None, default: bool) -> bool:
    """
    Returns whether an action needs to be done, based on whether the user required it and the default value of the
    runner.
    """
    return default if user is None else user


def _read_stream(stream: IO[bytes], stream_id: int, chunks: queue.SimpleQueue[tuple[int, bytes]]) -> None:
    """
    Read a command output stream until EOF, pushing each chunk to a queue shared by all the output streams.
    An empty chunk is always pushed last, to mark the end of the stream.

    Args:
        stream: The unbuffered output stream, where each read returns whatever data is available (up to the size).
        stream_id: The identifier of the stream, pushed alongside each chunk.
        chunks: The shared queue.
    """
    try:
        while chunk := stream.read(_READ_SIZE):
            chunks.put((stream_id, chunk))
    finally:
        chunks.put((stream_id, b""))


class Runner:
    """
    An instance of a shell command runner, used to run shell commands with a specific runner configuration.
    """

    def __init__(
        self,
        *,
        log_cmd: bool = False,
        log_output: bool = False,
        verify_return_code: bool = True,
        verify_stderr: bool = False,
        use_signal_names: bool = True,
        decoder_factory: _DecoderFactory = _default_decoder_factory,
    ) -> None:
        """
        Create a command runner.

        The configuration defines the default behavior of the subprocess which runs the shell command.
        Any of the settings can be overridden in individual calls to `run`.

        Args:
            log_cmd: Whether to log the executed command.
            log_output: Whether to log the live output of the command (while it is being executed).
            verify_return_code: Whether to raise an exception if the shell return code of the command is not `0`.
            verify_stderr: Whether to raise an exception if anything was written to stderr during the execution.
            use_signal_names:  Whether to log the name of the signal corresponding to a non-zero error code,
                               in case of result verification failure.
            decoder_factory: Callable that returns a fresh incremental decoder, used to decode the command output.
        """
        self._log_cmd = log_cmd
        self._log_output = log_output
        self._verify_return_code = verify_return_code
        self._verify_stderr = verify_stderr
        self._use_signal_names = use_signal_names
        self._decoder_factory = decoder_factory

    @staticmethod
    def _log(msg: str) -> None:
        """
        Log a message to the standard output.
        """
        sys.stdout.write(msg)
        sys.stdout.flush()

    def _decode_output(
        self,
        *,
        data: bytes | None,
        log_output: bool | None,
        decoder: codecs.IncrementalDecoder,
        final: bool,
    ) -> str:
        """
        Decode a partial output chunk of a single stream, and log it if required.

        Args:
            data: The partial output to decode.
            log_output: Whether to log the output, as supplied to `.run`.
            decoder: Stream decoder.
            final: Whether this is the last chunk, flushing any trailing incomplete bytes.

        Returns:
            The decoded output (possibly empty).
        """
        decoded_data = decoder.decode(data or b"", final)
        if decoded_data and _is_action_required(user=log_output, default=self._log_output):
            self._log(decoded_data)
        return decoded_data

    def _verify_result(
        self,
        *,
        result: ShellCmdResult,
        verify_return_code: bool | None,
        verify_stderr: bool | None,
        use_signal_names: bool | None,
    ) -> None:
        """
        Verify that the shell command executed successfully.
        The success is defined by a set of tests on the command outputs.

        Args:
            result: The command result object.
            verify_return_code: Whether to verify that the return code is `0`.
            verify_stderr: Whether to verify that the nothing was written to `stderr`.
            use_signal_names: Whether to use signal names when logging errors.

        Raises:
            ShpyxVerificationError: If verification failed.
        """
        success = True

        # Verify return code.
        if _is_action_required(user=verify_return_code, default=self._verify_return_code):
            success &= result.return_code == 0

        # Verify stderr.
        if _is_action_required(user=verify_stderr, default=self._verify_stderr):
            success &= not result.stderr

        if not success:
            return_code_str = str(result.return_code)

            # Add the signal name, if applicable.
            if _is_action_required(user=use_signal_names, default=self._use_signal_names):
                try:
                    signal_name: str = signal.Signals(result.return_code).name
                    return_code_str += f" ({signal_name})"
                except ValueError:
                    pass

            reason = (
                f"The command '{result.cmd}' failed with return code {return_code_str}.\n\n"
                f"Error output:\n{result.stderr}\n"
                f"All output:\n{result.all_output}"
            )
            raise ShpyxVerificationError(reason=reason, result=result)

    def run(
        self,
        args: str | list[str],
        *,
        # Runner configuration.
        log_cmd: bool | None = None,
        log_output: bool | None = None,
        verify_return_code: bool | None = None,
        verify_stderr: bool | None = None,
        use_signal_names: bool | None = None,
        # Command execution configuration.
        env: dict[str, str] | None = None,
        exec_dir: Path | str | None = None,
        unix_raw: bool = False,
        decoder_factory: _DecoderFactory | None = None,
    ) -> ShellCmdResult:
        """
        Run a shell command.

        Args:
            Command:
            -------
            args: The shell command arguments, can be a string (with the full command) or a list of strings.

            Runner configuration:
            -------------------
            log_cmd: Whether to log the executed command.
                     Runner default: `False`.
            log_output: Whether to log the live output of the command (while it is being executed).
                        Runner default: `False`.
            verify_return_code: Whether to raise an exception if the shell return code of the command is not `0`.
                                Runner default: `True`.
            verify_stderr: Whether to raise an exception if anything was written to stderr during the execution.
                           Runner default: `False`.
            use_signal_names:  Whether to log the name of the signal corresponding to a non-zero error code,
                               in case of result verification failure.
                               Runner default: `True`.

            Command execution configuration:
            ------------------------------
            env: Environment variables to set during the execution of the command (in addition to those of the parent
                 process, which will also be available to the subprocess).
            exec_dir: Custom path to execute the command in.
                      Runner default: `None`, which uses the current directory.
            unix_raw: (UNIX ONLY) Whether to use the `script` Unix utility to run the command.
                      This allows capturing all characters from the command output, including cursor movement and
                      colors. This can be useful when the command is an interactive shell, like `psql`.
                      Runner default: `False`.
            decoder_factory: Callable that returns a fresh incremental decoder, used to decode the command output.
                             Runner default: `None`, which uses the default decoder factory.

        Returns:
            The result, as a `ShellCmdResult` object.

        Raises:
            ShpyxOSNotSupportedError: The current OS is not supported for this operation.
            ShpyxInternalError: Internal error when executing the command.
        """
        tmp_file = tempfile.NamedTemporaryFile()  # noqa: SIM115

        if isinstance(args, str):
            # When a single string is passed, use an actual shell to support shell logic like bash piping.
            cmd_str = args
            use_shell = True

            if unix_raw:
                if _SYSTEM == "Linux":  # pragma: no branch, linux-only
                    # Old format: https://linux.die.net/man/1/script
                    # New format: https://man7.org/linux/man-pages/man1/script.1.html
                    args = f"script --return --quiet --command {shlex.quote(cmd_str)} {tmp_file.name}"
                elif _SYSTEM == "Darwin":  # pragma: no branch, darwin-only
                    # MacOS format: https://keith.github.io/xcode-man-pages/script.1.html
                    args = f"script -q {tmp_file.name} {cmd_str}"
                elif _SYSTEM == "Windows":  # pragma: no branch, windows-only
                    raise ShpyxOSNotSupportedError(f"Unsupported system: {_SYSTEM}")

        else:
            # When the arguments are a list, there is no need to use an actual shell.
            cmd_str = " ".join(args)
            use_shell = False

        # Log the command, if required.
        if _is_action_required(user=log_cmd, default=self._log_cmd):
            self._log(f"Running: {cmd_str}\n")

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
            p = subprocess.Popen(  # noqa: S603
                args,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # Unbuffered pipes, so that each read returns as soon as any data is available.
                bufsize=0,
                env=cmd_env,
                cwd=exec_dir,
            )
        except Exception as e:
            raise ShpyxInternalError("Failed to initialize subprocess (subprocess.Popen)") from e

        # Verify that all the pipes were properly configured.
        if not p.stdout:
            raise ShpyxInternalError("Failed to initialize subprocess (stdout pipe)")
        if not p.stderr:
            raise ShpyxInternalError("Failed to initialize subprocess (stderr pipe)")

        # Initialize the result object.
        result = ShellCmdResult(cmd=cmd_str)

        # Create a fresh decoder per stream (they are stateful and must not be shared).
        decoder_factory = decoder_factory or self._decoder_factory
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        all_output_parts: list[str] = []
        streams = (
            (p.stdout, decoder_factory(), stdout_parts),
            (p.stderr, decoder_factory(), stderr_parts),
        )

        # Read each output stream in its own thread, since a blocking read of one stream must not prevent the other
        # from being drained (otherwise the command may block on a full pipe). The chunks are consumed here in arrival
        # order, which keeps `all_output` interleaved as the command wrote it.
        chunks: queue.SimpleQueue[tuple[int, bytes]] = queue.SimpleQueue()
        readers = [
            threading.Thread(target=_read_stream, args=(stream, stream_id, chunks), daemon=True)
            for stream_id, (stream, _, _) in enumerate(streams)
        ]
        for reader in readers:
            reader.start()

        open_streams = len(streams)
        while open_streams:
            stream_id, chunk = chunks.get()
            _, decoder, parts = streams[stream_id]

            # An empty chunk marks the end of the stream, flushing any trailing incomplete bytes.
            final = not chunk
            if final:
                open_streams -= 1

            # Add the partial output to the result and log it, if needed.
            decoded_data = self._decode_output(data=chunk, decoder=decoder, log_output=log_output, final=final)
            parts.append(decoded_data)
            all_output_parts.append(decoded_data)

        for reader in readers:
            reader.join()
        p.wait()

        result.stdout = "".join(stdout_parts)
        result.stderr = "".join(stderr_parts)
        result.all_output = "".join(all_output_parts)

        # Cleanup.
        p.stdout.close()
        p.stderr.close()
        tmp_file.close()

        # Save return code.
        result.return_code = p.returncode

        # Verify that the command result is valid, based on the verification configuration.
        self._verify_result(
            result=result,
            verify_return_code=verify_return_code,
            verify_stderr=verify_stderr,
            use_signal_names=use_signal_names,
        )

        return result


# A runner object with default configuration.
_default_runner = Runner()

# The default run function, which can be used with `shpyx.run`.
run = _default_runner.run
