from shpyx.result import ShellCmdResult


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
        self.result = result


class ShpyxInternalError(ShpyxError):
    """
    An internal error during execution of the shell command.
    """


class ShpyxOSNotSupportedError(ShpyxError):
    """
    The current OS is not supported by the operation.
    """
