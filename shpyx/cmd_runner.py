import fcntl
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from shpyx.errors import InternalError, VerificationError
from shpyx.result import ShellCmdResult


def _is_action_required(user_value: Optional[bool], default_value: bool) -> bool:
    """
    Returns whether an action needs to be done, based on whether the user required it and the default value of the
    runner.
    """
    if user_value is True:
        # User required the action.
        return True
    elif user_value is False:
        # User required the action not to be taken.
        return False
    else:
        # User did not define whether the action needs to be done, use the default.
        return default_value


@dataclass
class ShellCmdRunnerConfig:
    """
    Create a shell command runner.

    The configuration given to the `ShellCmdRunner` constructor defines the default behavior of the subprocess which
    runs the shell command. Most of them can be overridden by the call to `.run`.
    """

    log_cmd: bool = False
    """Whether to log the executed command."""

    log_output: bool = False
    """Whether to log the live output of the command (while it is being executed)."""

    verify_return_code: bool = True
    """Whether to raise an exception if the shell return code of the command is not `0`."""

    verify_stderr: bool = False
    """Whether to raise an exception if the command wrote anything to stderr."""

    use_signal_names: bool = True
    """use_signal_names: Whether to log the name of the signal corresponding to a non-zero error code,
                                 in case of result verification failure."""


class ShellCmdRunner:
    """
    An instance of a shell command runner, which can be used to run shell commands based on a specific configuration.

    The configuration given to the constructor defines the default behavior of the subprocess which
    runs the shell command. Most of it can be overridden by the call to `.run`.
    """

    def __init__(self, config: ShellCmdRunnerConfig) -> None:
        self._config = config

    @staticmethod
    def _log(msg: str) -> None:
        """
        Log a message to the standard output.
        """
        msg_with_carriage_returns = msg.replace("\n", "\n\r")
        sys.stdout.write(msg_with_carriage_returns)
        sys.stdout.flush()

    def _maybe_log_cmd(self, cmd: str, log_cmd: Optional[bool]) -> None:
        """
        Log the command, if required by the user or by the default behavior.
        :param cmd: The command.
        :param log_cmd: Whether to log the command, as supplied to `.run`.
        """
        if _is_action_required(log_cmd, self._config.log_cmd):
            self._log(f"Running: {cmd}\n")

    def _add_stdout(self, result: ShellCmdResult, data: str, log_output: Optional[bool]) -> None:
        """
        Add partial stdout output to the result.
        :param result: The result object of the command.
        :param data: The partial stdout output to add.
        :param log_output: Whether to log the output, as supplied to `.run`.
        """
        if "" == data:
            return

        result.stdout += data
        result.all_output += data

        if _is_action_required(log_output, self._config.log_output):
            self._log(data)

    def _add_stderr(self, result: ShellCmdResult, data: str, log_output: Optional[bool]) -> None:
        """
        Add partial stderr output to the result.
        :param result: The result object of the command.
        :param data: The partial stdout output to add.
        :param log_output: Whether to log the output, as supplied to `.run`.
        """
        if "" == data:
            return

        result.stderr += data
        result.all_output += data

        if _is_action_required(log_output, self._config.log_output):
            self._log(data)

    def _verify_result(
        self, result: ShellCmdResult, verify_return_code: Optional[bool], verify_stderr: Optional[bool]
    ) -> None:
        """
        Verify that the shell command executed successfully.
        The success is defined by a set of tests on the command outputs.

        :param result: The command result object.
        :param verify_return_code: Whether to verify that the return code is `0`.
        :param verify_stderr: Whether to verify that the command did not write to `stderr`.
        """
        success = True

        if _is_action_required(verify_return_code, self._config.verify_return_code):
            success &= result.return_code == 0

        if _is_action_required(verify_stderr, self._config.verify_stderr):
            success &= result.stderr == ""

        if not success:
            return_code_str = str(result.return_code)
            if self._config.use_signal_names:
                try:
                    signal_name = signal.Signals(result.return_code).name
                    return_code_str += f" ({signal_name})"
                except ValueError:
                    pass

            reason = (
                f"The command '{result.cmd}' failed with return code {return_code_str}.\n\n"
                f"Error output:\n{result.stderr}\nAll output:\n{result.all_output}"
            )
            raise VerificationError(reason=reason, result=result)

    def run(
        self,
        cmd: str,
        *,
        log_cmd: Optional[bool] = False,
        log_output: Optional[bool] = False,
        verify_return_code: Optional[bool] = True,
        verify_stderr: Optional[bool] = False,
        env: Optional[dict[str, str]] = None,
        exec_dir: Optional[Union[Path, str]] = None,
    ) -> ShellCmdResult:
        """
        Run the given shell command.
        This is the heart of `shpyX`.

        :param cmd: The shell command to run in a subprocess.

        :param log_cmd: Whether to log the executed command.
        :param log_output: Whether to log the live output of the command (while it is being executed).

        :param verify_return_code: Whether to raise an exception if the shell return code of the command is not `0`.
        :param verify_stderr: Whether to raise an exception if the command wrote anything to stderr.

        :param env: Environment variables to set during the execution of the command (in addition to those of the parent
                    process, which will also be available to the subprocess).

        :param exec_dir: Path where the command will be executed.

        :return: The result, as a `ShellCmdResult` object.
        """

        # Log the command, if required.
        self._maybe_log_cmd(cmd, log_cmd)

        # Build the command environment variables.
        cmd_env = os.environ.copy()
        if env is not None:
            cmd_env = os.environ.copy() | env

        # Prepare the execution path.
        if exec_dir is not None:
            exec_dir = str(exec_dir)

        # Initialize the subprocess wrapper.
        p = subprocess.Popen(
            [cmd],
            shell=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=cmd_env,
            cwd=exec_dir,
        )

        # Verify that all the pipes were properly configured.
        if not (p and p.stdout and p.stderr):
            raise InternalError("Failed to initialize subprocess.")

        # Initialize the result object.
        result = ShellCmdResult(cmd=cmd)

        # Make all the command outputs non blocking, so that it can be interrupted.
        fcntl.fcntl(p.stdout.fileno(), fcntl.F_SETFL, fcntl.fcntl(p.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)
        fcntl.fcntl(p.stderr.fileno(), fcntl.F_SETFL, fcntl.fcntl(p.stderr.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)

        # Run the command.
        # The command runs in a subprocess and it's outputs are periodically checked and added to the result object.
        while p.poll() is None:
            stdout_data = ""
            stderr_data = ""

            # Poll both outputs for any new data.
            try:
                stdout_data = p.stdout.read()
            except TypeError:
                pass
            try:
                stderr_data = p.stderr.read()
            except TypeError:
                pass

            # Update the result object and log the outputs, if needed.
            self._add_stdout(result, stdout_data, log_output)
            self._add_stderr(result, stderr_data, log_output)

            time.sleep(0.1)

        # Get the remaining outputs and add them to the result.
        final_stdout, final_stderr = p.communicate()
        self._add_stdout(result, final_stdout, log_output)
        self._add_stderr(result, final_stderr, log_output)

        p.stdout.close()
        p.stderr.close()

        result.return_code = p.returncode

        # Verify that the command result is valid, based on the verification configuration.
        self._verify_result(result, verify_return_code, verify_stderr)

        return result


# A runner object with default configuration.
_default_runner = ShellCmdRunner(config=ShellCmdRunnerConfig())

# The default run function, which can be used with `shpyx.run`.
run = _default_runner.run

# Aliases of `run`.
ex = run
execute = run
