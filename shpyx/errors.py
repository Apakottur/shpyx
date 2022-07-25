from shpyx.result import ShellCmdResult


class ShpyXError(Exception):
    """
    Top level error for this package.
    """

    pass


class VerificationError(ShpyXError):
    """
    Raised when the output of a command fails verification.
    """

    def __init__(self, reason: str, result: ShellCmdResult):
        super().__init__(reason)
        self.reason = reason
        self.result = result


class InternalError(ShpyXError):
    """
    An internal error during execution of the shell command.
    """

    pass
