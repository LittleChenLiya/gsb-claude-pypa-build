# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

import pyproject_hooks
import pytest

import build

from build._requirements import CollectedRequirement, merge_requirements


def test_merge_requirements_merges_by_canonical_name() -> None:
    merged = merge_requirements(
        ['Foo_Bar >= 1.0'],
        ['foo-bar < 3', 'other-dep'],
    )

    assert set(merged) == {'foo-bar', 'other-dep'}
    entries = merged['foo-bar']
    assert [entry.source for entry in entries] == ['static', 'dynamic']
    assert [entry.requirement for entry in entries] == ['Foo_Bar >= 1.0', 'foo-bar < 3']
    assert all(entry.name == 'foo-bar' for entry in entries)


def test_merge_requirements_preserves_pep508_markers() -> None:
    marker_decl = 'dep >= 1.0; python_version < "3.12" and extra == "test"'
    merged = merge_requirements([marker_decl], [])

    assert merged['dep'] == [CollectedRequirement(name='dep', requirement=marker_decl, source='static')]


def test_merge_requirements_invalid_entries_report_indices() -> None:
    with pytest.raises(build.InvalidRequirementsError) as exc_info:
        merge_requirements(
            ['ok-static', 'bad req (', 'also bad ;;'],
            ['ok-dynamic', 'still not valid !!!'],
        )

    assert exc_info.value.errors == [
        ('static', 1, 'bad req ('),
        ('static', 2, 'also bad ;;'),
        ('dynamic', 1, 'still not valid !!!'),
    ]
    message = str(exc_info.value)
    assert 'static[1]' in message
    assert 'static[2]' in message
    assert 'dynamic[1]' in message


def test_collect_requirements_merges_static_and_dynamic(
    package_test_dynamic_requirements: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    count_file = tmp_path / 'hook-calls.txt'
    monkeypatch.setenv('BUILD_TEST_HOOK_COUNT_FILE', str(count_file))

    builder = build.ProjectBuilder(package_test_dynamic_requirements, runner=pyproject_hooks.quiet_subprocess_runner)
    merged = builder.collect_requirements('wheel')

    # static and dynamic declarations for the same package are merged under
    # the canonical name, keeping their source and original PEP 508 string
    assert set(merged) == {'static-only-dep', 'shared-pkg', 'dynamic-only-dep'}

    shared = merged['shared-pkg']
    assert [entry.source for entry in shared] == ['static', 'dynamic']
    assert shared[0].requirement == "Shared-Pkg; python_version >= '3.10'"
    assert shared[1].requirement == 'shared-pkg >= 2.0; python_version < "3.99"'

    assert merged['static-only-dep'] == [
        CollectedRequirement(name='static-only-dep', requirement='static-only-dep >= 1.0', source='static')
    ]
    assert merged['dynamic-only-dep'] == [
        CollectedRequirement(name='dynamic-only-dep', requirement='dynamic-only-dep[extra] ~= 1.2', source='dynamic')
    ]

    # the hook was invoked exactly once
    assert count_file.read_text(encoding='utf-8').splitlines() == ['get_requires_for_build_wheel']


def test_collect_requirements_sdist_uses_matching_hook(
    package_test_dynamic_requirements: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    count_file = tmp_path / 'hook-calls.txt'
    monkeypatch.setenv('BUILD_TEST_HOOK_COUNT_FILE', str(count_file))

    builder = build.ProjectBuilder(package_test_dynamic_requirements, runner=pyproject_hooks.quiet_subprocess_runner)
    merged = builder.collect_requirements('sdist')

    assert set(merged) == {'static-only-dep', 'shared-pkg'}
    assert count_file.read_text(encoding='utf-8').splitlines() == ['get_requires_for_build_sdist']


def test_collect_requirements_invalid_declarations_raise_with_indices(
    package_test_invalid_dynamic_requirements: str,
) -> None:
    builder = build.ProjectBuilder(package_test_invalid_dynamic_requirements, runner=pyproject_hooks.quiet_subprocess_runner)

    with pytest.raises(build.InvalidRequirementsError) as exc_info:
        builder.collect_requirements('wheel')

    assert exc_info.value.errors == [
        ('static', 1, 'not a valid requirement !!!'),
        ('static', 2, 'another bad ;; one'),
        ('dynamic', 1, 'also not valid !!!'),
    ]
    message = str(exc_info.value)
    assert 'static[1]' in message
    assert 'dynamic[1]' in message
