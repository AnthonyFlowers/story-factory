from __future__ import annotations


class SFError(Exception):
    """A user-facing error. code 1 = runtime error, 2 = usage or config error."""

    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code
