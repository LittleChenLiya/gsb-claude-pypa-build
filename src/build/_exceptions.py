from __future__ import annotations

import typing


TYPE_CHECKING = False

if TYPE_CHECKING:
    import subprocess

    from collections.abc import Sequence


class BuildException(Exception):
    """
    Exception raised by ``build`` when a build cannot proceed.
    """


class BuildBackendException(Exception):
    """
    Exception raised when a backend operation fails.
    """

    def __init__(
        self,
        exception: Exception,
        description: str | None = None,
    ) -> None:
        super().__init__()
        self.exception: Exception = exception
        self._description = description

    def __str__(self) -> str:
        if self._description:
            return self._description
        return f'Backend operation failed: {self.exception!r}'


class BuildSystemTableValidationError(BuildException):
    """
    Exception raised when the ``[build-system]`` table in pyproject.toml is invalid.
    """

    def __str__(self) -> str:
        return f'Failed to validate `build-system` in pyproject.toml: {self.args[0]}'


class RequirementDeclarationError(typing.NamedTuple):
    """
    Details of a single invalid requirement declaration.
    """

    #: Where the declaration came from (``'static'`` or ``'dynamic'``).
    source: str
    #: Position of the declaration within its source list.
    index: int
    #: The offending declaration.
    requirement: str
    #: The parser error message.
    message: str


class InvalidRequirementsError(BuildException):
    """
    Exception raised when one or more requirement declarations are invalid.

    All offending declarations are reported via :attr:`errors`, each with
    its source and index; no merged requirement list is produced.
    """

    def __init__(self, errors: Sequence[RequirementDeclarationError]) -> None:
        super().__init__()
        self.errors: tuple[RequirementDeclarationError, ...] = tuple(errors)

    def __str__(self) -> str:
        lines = [f'Invalid requirement declarations ({len(self.errors)}):']
        lines += [f'  {error.source}[{error.index}]: {error.requirement!r} ({error.message})' for error in self.errors]
        return '\n'.join(lines)


class FailedProcessError(Exception):
    """
    Exception raised when a setup or preparation operation fails.
    """

    def __init__(self, exception: subprocess.CalledProcessError, description: str) -> None:
        super().__init__()
        self.exception: subprocess.CalledProcessError = exception
        self._description = description

    def __str__(self) -> str:
        return self._description


class TypoWarning(Warning):
    """
    Warning raised when a possible typo is found.
    """
