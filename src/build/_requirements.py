# SPDX-License-Identifier: MIT

from __future__ import annotations


__lazy_modules__ = {
    'dataclasses',
    'packaging',
    'packaging.requirements',
    'packaging.utils',
    f'{__spec__.parent}._exceptions',
}

import dataclasses

import packaging.requirements
import packaging.utils

from ._exceptions import InvalidRequirementsError


TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclasses.dataclass(frozen=True)
class CollectedRequirement:
    """
    A single build requirement declaration together with its origin.

    The original PEP 508 string is preserved verbatim -- environment markers
    and version constraints are kept as declared and are never evaluated.
    """

    name: str
    """Canonicalized (PEP 503) package name, used as the merge key."""

    requirement: str
    """The original PEP 508 requirement string, markers included."""

    source: str
    """Origin of the declaration: ``'static'`` (``build-system.requires``) or ``'dynamic'`` (build hook result)."""


def merge_requirements(
    static: Sequence[str],
    dynamic: Sequence[str],
) -> dict[str, list[CollectedRequirement]]:
    """
    Merge static and dynamic requirement declarations by canonical package name.

    Declarations from both sources are parsed as PEP 508 requirements and
    grouped under their canonicalized (PEP 503) package name. Each entry
    keeps the original requirement string -- including any environment
    markers -- and records whether it came from the ``static`` or the
    ``dynamic`` source. Entries from the same source keep their original
    relative order, and static entries precede dynamic ones.

    Nothing is installed and no transitive resolution is performed.

    :param static: Declarations from ``build-system.requires``
    :param dynamic: Declarations returned by a ``get_requires_for_build_*`` hook
    :returns: Mapping of canonical package name to the declarations for it
    :raises InvalidRequirementsError: If any declaration is not a valid
        PEP 508 requirement. The error reports the source and index of each
        offending entry; no merged mapping is returned in that case.
    """
    collected: list[CollectedRequirement] = []
    errors: list[tuple[str, int, str]] = []
    for source, declarations in (('static', static), ('dynamic', dynamic)):
        for index, declaration in enumerate(declarations):
            try:
                requirement = packaging.requirements.Requirement(declaration)
            except packaging.requirements.InvalidRequirement:
                errors.append((source, index, declaration))
                continue
            collected.append(
                CollectedRequirement(
                    name=packaging.utils.canonicalize_name(requirement.name),
                    requirement=declaration,
                    source=source,
                )
            )
    if errors:
        raise InvalidRequirementsError(errors)

    merged: dict[str, list[CollectedRequirement]] = {}
    for entry in collected:
        merged.setdefault(entry.name, []).append(entry)
    return merged


__all__ = [
    'CollectedRequirement',
    'merge_requirements',
]
