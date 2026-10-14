from dataclasses import dataclass, field


@dataclass
class ShellCmdResult:
    """
    The result of an execution of a shell command.
    """

    # The command that was executed.
    cmd: str

    # The output streams of the command: Standard Output and Standard Error.
    stdout: str = ""
    stderr: str = ""

    # All the output of the command (stdout + stderr) as it would have appeared on screen.
    # Note that this is NOT necessarily equal to `self.stdout + self.stderr`,
    # as the two streams are written in parallel.
    all_output: str = ""

    # The return code of the command.
    # Apart from 0 meaning success (which is also not always the case), there is no general mapping of return codes
    # to errors.
    return_code: int = -1

    # The output parts collected while the command runs, joined once it exits (for performance).
    _stdout_parts: list[str] = field(default_factory=list, init=False, repr=False, compare=False)
    _stderr_parts: list[str] = field(default_factory=list, init=False, repr=False, compare=False)
    _all_output_parts: list[str] = field(default_factory=list, init=False, repr=False, compare=False)

    def _add_output(self, *, stdout: str, stderr: str) -> None:
        """
        Add decoded partial outputs, keeping `all_output` in arrival order.
        """
        self._stdout_parts.append(stdout)
        self._stderr_parts.append(stderr)
        self._all_output_parts += (stdout, stderr)

    def _join_output(self) -> None:
        """
        Concatenate all the collected output parts into the output fields.
        """
        self.stdout = "".join(self._stdout_parts)
        self.stderr = "".join(self._stderr_parts)
        self.all_output = "".join(self._all_output_parts)
