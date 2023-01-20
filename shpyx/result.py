from dataclasses import dataclass


@dataclass
class ShellCmdResult:
    """
    The result of an execution of a shell command.
    """

    """The command that was executed"""
    cmd: str

    """The output streams of the command: Standard Output and Standard Error"""
    stdout: str = ""
    stderr: str = ""

    """
    All the output of the command (stdout + stderr) as it would have appeared on screen.
    Note that this is NOT necessarily equal to `self.stdout + self.stderr`,
    as the two streams are written in parallel.
    """
    all_output: str = ""

    """
    The return code of the command.
    Apart from 0 meaning success (which is also not always the case), there is no general mapping of return codes
    to errors.
    """
    return_code: int = -1
