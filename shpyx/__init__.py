import fcntl
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ShellCmdResult:
    cmd: str

    # The output streams of the command: Standard Output and Standard Error
    stdout: str = ""
    stderr: str = ""

    # All the output of the command (stdout + stderr) as it would have appeared on screen (this is NOT equal to
    # stdout + stderr, as the two streams are written in parallel)
    all_output: str = ""

    # The return code of the command. Note that there is not unified convention regarding the value of the return code.
    return_code: int = -1


class ShellCmdRunner:
    def __init__(self, log_cmd=False, log_output=True, verify_return_code=True, verify_stderr=False):
        """
        Create a shell command runner.

        :param log_cmd: Whether to log the executed command
        :param log_output: Whether to log the output of the command (while it is being executed)

        :param verify_return_code: Whether to raise an exception if the bash return code of the command is not `0`.
        :param verify_stderr: Whether to raise an exception if the command printed to stderr.
        """
        self._log_cmd = log_cmd
        self._log_output = log_output
        self._verify_return_code = verify_return_code
        self._verify_stderr = verify_stderr

    @staticmethod
    def _log(msg: str):
        sys.stdout.write(msg)
        sys.stdout.flush()

    def _maybe_log_cmd(self, cmd: str, log_cmd: Optional[bool]):
        if (log_cmd is False) and (self._log_cmd is False):
            return

        self._log(f"Running: {cmd}\n")

    def _add_stdout(self, result: ShellCmdResult, data: str, log_output: Optional[bool]):
        if "" == data:
            return

        result.stdout += data
        result.all_output += data

        if (log_output is False) and (self._log_output is False):
            return

        self._log(data)

    def _add_stderr(self, result: ShellCmdResult, data: str, log_output: Optional[bool]):
        if "" == data:
            return

        result.stderr += data
        result.all_output += data

        if (log_output is False) and (self._log_output is False):
            return

        self._log(data)

    def _verify_result(self, result: ShellCmdResult, verify_return_code: Optional[bool], verify_stderr: Optional[bool]):
        success = True
        if verify_return_code or (verify_return_code is None and self._verify_return_code):
            success &= result.return_code == 0

        if verify_stderr or (verify_stderr is None and self._verify_stderr):
            success &= result.return_code == ""

        if not success:
            raise RuntimeError(
                f"The command '{result.cmd}' failed with return code {result.return_code}.\n\n"
                f"Error output:\n{result.stderr}\nAll output:\n{result.all_output}"
            )

    def run(
        self,
        cmd: str,
        *,
        log_cmd: Optional[bool] = False,
        log_output: Optional[bool] = True,
        verify_return_code: Optional[bool] = True,
        verify_stderr: Optional[bool] = False,
    ) -> ShellCmdResult:

        self._maybe_log_cmd(cmd, log_cmd)

        p = subprocess.Popen([cmd], shell=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        result = ShellCmdResult(cmd=cmd)

        fcntl.fcntl(p.stdout.fileno(), fcntl.F_SETFL, fcntl.fcntl(p.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)
        fcntl.fcntl(p.stderr.fileno(), fcntl.F_SETFL, fcntl.fcntl(p.stderr.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK)

        while p.poll() is None:
            try:
                self._add_stdout(result, p.stdout.read(), log_output)
            except TypeError:
                pass
            try:
                self._add_stderr(result, p.stdout.read(), log_output)
            except TypeError:
                pass
            time.sleep(0.1)

        final_stdout, final_stderr = p.communicate()
        self._add_stdout(result, final_stdout, log_output)
        self._add_stderr(result, final_stderr, log_output)

        p.stdout.close()
        p.stderr.close()

        result.return_code = p.returncode

        self._verify_result(result, verify_return_code, verify_stderr)

        return result


_default_runner = ShellCmdRunner()

run = _default_runner.run
ex = run
execute = run
