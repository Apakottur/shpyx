import signal

from shpyx._errors import ShpyxVerificationError
from shpyx._result import ShellCmdResult


def verify_result(
    *,
    result: ShellCmdResult,
    verify_return_code: bool,
    verify_stderr: bool,
    use_signal_names: bool,
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
    if verify_return_code:
        success &= result.return_code == 0

    # Verify stderr.
    if verify_stderr:
        success &= not result.stderr

    if not success:
        return_code_str = str(result.return_code)

        # Add the signal name, if the command was killed by a signal (`subprocess` returns `-N` for signal `N`).
        if use_signal_names and result.return_code < 0:
            try:
                signal_name: str = signal.Signals(-result.return_code).name
                return_code_str += f" ({signal_name})"
            except ValueError:
                pass

        reason = (
            f"The command '{result.cmd}' failed with return code {return_code_str}.\n\n"
            f"Error output:\n{result.stderr}\n"
            f"All output:\n{result.all_output}"
        )
        raise ShpyxVerificationError(reason=reason, result=result)
