import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

from shpyx.errors import ShpyxInternalError, ShpyxVerificationError
from shpyx.result import ShellCmdResult

"""The platform system (Linux/Darwin/Windows/Java) is used for platform specific code"""
_SYSTEM = platform.system()


if _SYSTEM != "Windows":
    import fcntl


def _is_action_required(user_value: Optional[bool], default_value: bool) -> bool:
    """
    Returns whether an action needs to be done, based on whether the user required it and the default value of the
    runner.
    """
    if user_value is True:
        # The user explicitly set the value to `True`.
        return True
    elif user_value is False:
        # The user explicitly set the value to `False`.
        return False
    else:
        # The user did not provide a value for the action, use the default.
        return default_value


class Runner:
    """
    An instance of a shell command runner, used to run shell commands based on a specific configuration.
    """

    def __init__(
        self,
        *,
        log_cmd: bool = False,
        log_output: bool = False,
        verify_return_code: bool = True,
        verify_stderr: bool = False,
        use_signal_names: bool = True,
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
        """
        self._log_cmd = log_cmd
        self._log_output = log_output
        self._verify_return_code = verify_return_code
        self._verify_stderr = verify_stderr
        self._use_signal_names = use_signal_names

    @staticmethod
    def _log(msg: Union[bytes, str]) -> None:
        """
        Log a message to the standard output.
        """
        if isinstance(msg, bytes):
            sys.stdout.buffer.write(msg)
        else:
            sys.stdout.write(msg)

        sys.stdout.flush()

    def _add_stdout(self, result: ShellCmdResult, data: Optional[bytes], log_output: Optional[bool]) -> None:
        """
        Add partial stdout output to the result.

        Args:
            result: The result object of the command.
            data: The partial stdout output to add.
            log_output: Whether to log the output, as supplied to `.run`.
        """
        if data is None:
            return

        result.stdout += data.decode()
        result.all_output += data.decode()

        if _is_action_required(log_output, self._log_output):
            self._log(data)

    def _add_stderr(self, result: ShellCmdResult, data: Optional[bytes], log_output: Optional[bool]) -> None:
        """
        Add partial stderr output to the result.

        Args:
            result: The result object of the command.
            data: The partial stderr output to add.
            log_output: Whether to log the output, as supplied to `.run`.
        """
        if data is None:
            return

        result.stderr += data.decode()
        result.all_output += data.decode()

        if _is_action_required(log_output, self._log_output):
            self._log(data)

    def _verify_result(
        self,
        result: ShellCmdResult,
        verify_return_code: Optional[bool],
        verify_stderr: Optional[bool],
    ) -> None:
        """
        Verify that the shell command executed successfully.
        The success is defined by a set of tests on the command outputs.

        Args:
            result: The command result object.
            verify_return_code: Whether to verify that the return code is `0`.
            verify_stderr: Whether to verify that the nothing was written to `stderr`.

        Raises:
            ShpyxVerificationError: If verification failed.
        """
        success = True

        # Verify return code.
        if _is_action_required(verify_return_code, self._verify_return_code):
            success &= result.return_code == 0

        # Verify stderr.
        if _is_action_required(verify_stderr, self._verify_stderr):
            success &= result.stderr == ""

        if not success:
            return_code_str = str(result.return_code)

            # Add the signal name, if applicable.
            if self._use_signal_names:
                try:
                    signal_name = signal.Signals(result.return_code).name
                    return_code_str += f" ({signal_name})"
                except ValueError:
                    pass

            reason = (
                f"The command '{result.cmd}' failed with return code {return_code_str}.\n\n"
                f"Error output:\n{result.stderr}\nAll output:\n{result.all_output}"
            )
            raise ShpyxVerificationError(reason=reason, result=result)

    def run(
        self,
        args: Union[str, List[str]],
        *,
        log_cmd: Optional[bool] = None,
        log_output: Optional[bool] = None,
        verify_return_code: Optional[bool] = None,
        verify_stderr: Optional[bool] = None,
        env: Optional[Dict[str, str]] = None,
        exec_dir: Optional[Union[Path, str]] = None,
    ) -> ShellCmdResult:
        """
        Run a shell command.

        Apart from the command itself, all arguments are optional.
        The default values of the arguments can be found in `ShellCmdRunnerConfig`.

        Args:
            args: The shell command arguments, can be a string (with the full command) or a list of strings.
            log_cmd: Whether to log the executed command.
            log_output: Whether to log the live output of the command (while it is being executed).
            verify_return_code: Whether to raise an exception if the shell return code of the command is not `0`.
            verify_stderr: Whether to raise an exception if anything was written to stderr during the execution.
            env: Environment variables to set during the execution of the command (in addition to those of the parent
                 process, which will also be available to the subprocess).
            exec_dir: Custom path to execute the command in (defaults to current directory).

        Returns: The result, as a `ShellCmdResult` object.

        Raises:
            ShpyxInternalError: Internal error when executing the command.
        """

        if isinstance(args, str):
            # When a single string is passed, use an actual shell to support shell logic like bash piping.
            cmd_str = args
            use_shell = True
        else:
            # When the arguments are a list, there is no need to use an actual shell.
            cmd_str = " ".join(args)
            use_shell = False

        # Log the command, if required.
        if _is_action_required(log_cmd, self._log_cmd):
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
        p = subprocess.Popen(
            args,
            shell=use_shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=cmd_env,
            cwd=exec_dir,
        )

        # Verify that all the pipes were properly configured.
        if not (p and p.stdout and p.stderr):
            raise ShpyxInternalError("Failed to initialize subprocess.")

        # Initialize the result object.
        result = ShellCmdResult(cmd=cmd_str)

        # Make all the command outputs non-blocking, so that it can be interrupted.
        if _SYSTEM != "Windows":
            fcntl.fcntl(p.stdout.fileno(), fcntl.F_SETFL, fcntl.fcntl(p.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)
            fcntl.fcntl(p.stderr.fileno(), fcntl.F_SETFL, fcntl.fcntl(p.stderr.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)

        # Run the command in a subprocess, periodically checking for outputs.
        while p.poll() is None:
            stdout_data = None
            stderr_data = None

            # Poll both outputs for any new data.
            try:
                stdout_data = p.stdout.read()
            except TypeError:
                pass
            try:
                stderr_data = p.stderr.read()
            except TypeError:
                pass

            # Add partial outputs to result and log them, if needed.
            self._add_stdout(result, stdout_data, log_output)
            self._add_stderr(result, stderr_data, log_output)

            time.sleep(0.01)

        # Get the remaining outputs and add them to the result.
        final_stdout, final_stderr = p.communicate()
        self._add_stdout(result, final_stdout, log_output)
        self._add_stderr(result, final_stderr, log_output)

        # Cleanup subprocess object.
        p.stdout.close()
        p.stderr.close()

        # Save return code.
        result.return_code = p.returncode

        # Verify that the command result is valid, based on the verification configuration.
        self._verify_result(result, verify_return_code, verify_stderr)

        return result


# A runner object with default configuration.
_default_runner = Runner()

# The default run function, which can be used with `shpyx.run`.
run = _default_runner.run
