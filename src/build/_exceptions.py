from __future__ import annotations


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


class InvalidRequirementsError(BuildException):
    """
    Exception raised when one or more requirement declarations are invalid.

    The offending declarations are carried as ``(source, index, requirement)``
    tuples in :attr:`errors`, where ``source`` is ``'static'`` (the
    ``build-system.requires`` table) or ``'dynamic'`` (the result of a
    ``get_requires_for_build_*`` hook) and ``index`` is the position of the
    declaration within that source list.
    """

    def __init__(self, errors: Sequence[tuple[str, int, str]]) -> None:
        self.errors: list[tuple[str, int, str]] = list(errors)
        super().__init__(str(self))

    def __str__(self) -> str:
        lines = '\n'.join(f'\t{source}[{index}]: {requirement!r}' for source, index, requirement in self.errors)
        return f'Invalid requirement declarations:\n{lines}'


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
