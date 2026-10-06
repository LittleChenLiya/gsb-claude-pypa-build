# SPDX-License-Identifier: MIT

from __future__ import annotations


__lazy_modules__ = {
    'pathlib',
    'tempfile',
    'packaging.requirements',
    'packaging.utils',
    f'{__spec__.parent}._compat',
    f'{__spec__.parent}._exceptions',
    f'{__spec__.parent}.env',
}

import dataclasses
import pathlib
import tempfile

import packaging.requirements
import packaging.utils
import pyproject_hooks

from . import ProjectBuilder
from ._compat import importlib
from ._exceptions import InvalidRequirementsError, RequirementDeclarationError
from .env import DefaultIsolatedEnv


TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Sequence

    from ._types import ConfigSettings, Distribution, StrPath, SubprocessRunner


def _project_wheel_metadata(builder: ProjectBuilder) -> importlib.metadata.PackageMetadata:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(builder.metadata_path(tmpdir))
        metadata = importlib.metadata.PathDistribution(path).metadata
        assert metadata is not None
        return metadata


def project_wheel_metadata(
    source_dir: StrPath,
    isolated: bool = True,
    *,
    runner: SubprocessRunner = pyproject_hooks.quiet_subprocess_runner,
) -> importlib.metadata.PackageMetadata:
    """
    Return the wheel metadata for a project.

    Uses the ``prepare_metadata_for_build_wheel`` hook if available,
    otherwise ``build_wheel``.

    :param source_dir: Project source directory
    :param isolated: Whether or not to run invoke the backend in the current
                     environment or to create an isolated one and invoke it
                     there.
    :param runner: An alternative runner for backend subprocesses
    """

    if isolated:
        with DefaultIsolatedEnv() as env:
            builder = ProjectBuilder.from_isolated_env(
                env,
                source_dir,
                runner=runner,
            )
            env.install(builder.build_system_requires, _fresh=True)
            env.install(builder.get_requires_for_build('wheel'))
            return _project_wheel_metadata(builder)
    else:
        builder = ProjectBuilder(
            source_dir,
            runner=runner,
        )
        return _project_wheel_metadata(builder)


#: Source tag for requirements declared statically in ``build-system.requires``.
STATIC_SOURCE = 'static'

#: Source tag for requirements returned by the ``get_requires_for_build_*`` hook.
DYNAMIC_SOURCE = 'dynamic'


@dataclasses.dataclass(frozen=True)
class CollectedRequirement:
    """
    A build requirement collected from static and/or dynamic declarations.

    Declarations are merged by canonicalized package name; the original
    PEP 508 strings (including extras and markers) are preserved.
    """

    #: Canonicalized (normalized) package name.
    name: str
    #: Original PEP 508 requirement strings, static declarations first.
    requirements: tuple[str, ...]
    #: Origins of the declarations: ``'static'`` and/or ``'dynamic'``.
    sources: frozenset[str]


def _merge_requirements(static: Sequence[str], dynamic: Sequence[str]) -> list[CollectedRequirement]:
    """
    Merge static and dynamic requirement declarations by canonicalized
    package name, keeping track of the origin of each declaration.

    :raises build.InvalidRequirementsError: if any declaration is not a
        valid PEP 508 requirement; all offending entries are reported with
        their source and index and no merged list is returned
    """
    merged: dict[str, tuple[list[str], set[str]]] = {}
    errors: list[RequirementDeclarationError] = []
    for source, declarations in ((STATIC_SOURCE, static), (DYNAMIC_SOURCE, dynamic)):
        for index, declaration in enumerate(declarations):
            try:
                requirement = packaging.requirements.Requirement(declaration)
            except packaging.requirements.InvalidRequirement as exception:
                errors.append(RequirementDeclarationError(source, index, declaration, str(exception)))
                continue
            name = packaging.utils.canonicalize_name(requirement.name)
            requirements, sources = merged.setdefault(name, ([], set()))
            requirements.append(declaration)
            sources.add(source)
    if errors:
        raise InvalidRequirementsError(errors)
    return [
        CollectedRequirement(name, tuple(requirements), frozenset(sources)) for name, (requirements, sources) in merged.items()
    ]


def collect_requirements(
    source_dir: StrPath,
    distribution: Distribution = 'wheel',
    *,
    config_settings: ConfigSettings | None = None,
    runner: SubprocessRunner = pyproject_hooks.quiet_subprocess_runner,
) -> list[CollectedRequirement]:
    """
    Collect the build requirements for a project distribution.

    Merges the static ``build-system.requires`` declarations with the
    dynamic ``get_requires_for_build_<distribution>`` hook result, keyed by
    canonicalized package name and preserving the origin of each
    declaration. The hook is called exactly once. Nothing is installed and
    dependencies are not resolved recursively.

    :param source_dir: Project source directory
    :param distribution: Distribution to collect requirements for
        (``sdist``, ``wheel`` or ``editable``)
    :param config_settings: Config settings for the build backend
    :param runner: An alternative runner for backend subprocesses
    :raises build.InvalidRequirementsError: if any declaration is not a
        valid PEP 508 requirement
    """
    builder = ProjectBuilder(source_dir, runner=runner)
    static = list(builder._build_system['requires'])
    dynamic = builder._get_requires_for_build(distribution, config_settings)
    return _merge_requirements(static, dynamic)


__all__ = [
    'CollectedRequirement',
    'collect_requirements',
    'project_wheel_metadata',
]
