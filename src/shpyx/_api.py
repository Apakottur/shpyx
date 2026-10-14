from __future__ import annotations

from typing import TYPE_CHECKING

from shpyx._execute import execute
from shpyx._output import _default_decoder_factory

if TYPE_CHECKING:
    import os
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from shpyx._output import _DecoderFactory
    from shpyx._result import ShellCmdResult


def _is_action_required(*, user: bool | None, default: bool) -> bool:
    """
    Returns whether an action needs to be done, based on whether the user required it and the default value of the
    runner.
    """
    return default if user is None else user


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
            use_signal_names:  Whether to log the name of the signal that killed the command (negative return code),
                               in case of result verification failure.
            decoder_factory: Callable that returns a fresh incremental decoder, used to decode the command output.
        """
        self._log_cmd = log_cmd
        self._log_output = log_output
        self._verify_return_code = verify_return_code
        self._verify_stderr = verify_stderr
        self._use_signal_names = use_signal_names
        self._decoder_factory = decoder_factory

    def run(
        self,
        args: str | Sequence[str | os.PathLike[str]],
        *,
        # Runner configuration.
        log_cmd: bool | None = None,
        log_output: bool | None = None,
        verify_return_code: bool | None = None,
        verify_stderr: bool | None = None,
        use_signal_names: bool | None = None,
        # Command execution configuration.
        env: Mapping[str, str] | None = None,
        exec_dir: Path | str | None = None,
        unix_raw: bool = False,
        decoder_factory: _DecoderFactory | None = None,
    ) -> ShellCmdResult:
        """
        Run a shell command.

        Args:
            Command:
            -------
            args: The shell command arguments, can be a string (with the full command) or a sequence of strings
                  and paths.

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
            use_signal_names:  Whether to log the name of the signal that killed the command (negative return code),
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
                      Supported for both string and list arguments; the command is always run through a shell.
                      Supported on Linux and macOS, raises `ShpyxOSNotSupportedError` on any other system.
                      Runner default: `False`.
            decoder_factory: Callable that returns a fresh incremental decoder, used to decode the command output.
                             Runner default: `None`, which uses the default decoder factory.

        Returns:
            The result, as a `ShellCmdResult` object.

        Raises:
            ShpyxOSNotSupportedError: The current OS is not supported for this operation.
            ShpyxInternalError: Internal error when executing the command.
        """
        return execute(
            args,
            log_cmd=_is_action_required(user=log_cmd, default=self._log_cmd),
            log_output=_is_action_required(user=log_output, default=self._log_output),
            verify_return_code=_is_action_required(user=verify_return_code, default=self._verify_return_code),
            verify_stderr=_is_action_required(user=verify_stderr, default=self._verify_stderr),
            use_signal_names=_is_action_required(user=use_signal_names, default=self._use_signal_names),
            env=env,
            exec_dir=exec_dir,
            unix_raw=unix_raw,
            decoder_factory=decoder_factory or self._decoder_factory,
        )


# A runner object with default configuration.
_default_runner = Runner()

# The default run function, which can be used with `shpyx.run`.
run = _default_runner.run
