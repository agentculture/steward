"""StewardError and exit-code policy.

Every failure inside steward raises :class:`StewardError`. The top-level
``main()`` catches it, formats via :mod:`steward.cli._output`, and exits with
:attr:`StewardError.code`. This guarantees:

* no Python traceback leaks to stderr;
* every error has a structured shape ``{code, message, remediation}``;
* the exit-code policy is centralised in one place.
"""

from __future__ import annotations

from dataclasses import dataclass

EXIT_SUCCESS = 0
EXIT_USER_ERROR = 1
EXIT_ENV_ERROR = 2


@dataclass
class StewardError(Exception):
    """Structured error raised within steward; carries a remediation hint."""

    code: int
    message: str
    remediation: str = ""

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "remediation": self.remediation,
        }
