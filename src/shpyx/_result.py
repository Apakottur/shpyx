from dataclasses import dataclass


@dataclass
class ShellCmdResult:
    """
    The result of an execution of a shell command.

    Attributes:
        cmd: The command that was executed.
        stdout: The Standard Output of the command.
        stderr: The Standard Error of the command.
        all_output: All the output of the command (stdout + stderr) as it would have appeared on screen.
            Note that this is NOT necessarily equal to `stdout + stderr`, as the two streams are written in parallel.
        return_code: The return code of the command.
            Apart from 0 meaning success (which is also not always the case), there is no general mapping of return
            codes to errors.
    """

    cmd: str
    stdout: str = ""
    stderr: str = ""
    all_output: str = ""
    return_code: int = -1
