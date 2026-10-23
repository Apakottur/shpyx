from shpyx._result import ShellCmdResult


class ShpyxError(Exception):
    """
    Top level error for errors raised by the shpyx package.
    """


class ShpyxVerificationError(ShpyxError):
    """
    The execution of a shell command was NOT successful.
    Note that the conditions for success are configurable.
    """

    def __init__(self, reason: str, result: ShellCmdResult) -> None:
        super().__init__(reason)
        self.reason = reason
        """
        The reason the verification failed, naming the failed checks.
        """

        self.result = result
        """
        The result of the command.
        """


class ShpyxInternalError(ShpyxError):
    """
    An internal error during execution of the shell command.
    """


class ShpyxOSNotSupportedError(ShpyxError):
    """
    The current OS is not supported by the operation.
    """
