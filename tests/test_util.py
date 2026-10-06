# SPDX-License-Identifier: MIT

from __future__ import annotations

import importlib.util
import re
import unittest.mock

import pyproject_hooks
import pytest
import pytest_mock

import build.util


@pytest.mark.parametrize('isolated', [False, pytest.param(True, marks=[pytest.mark.network, pytest.mark.isolated])])
def test_wheel_metadata(package_test_setuptools: str, isolated: bool) -> None:
    metadata = build.util.project_wheel_metadata(package_test_setuptools, isolated)

    # Setuptools < v69.0.3 (https://github.com/pypa/setuptools/pull/4159) normalized this to dashes
    assert metadata['name'].replace('-', '_') == 'test_setuptools'
    assert metadata['version'] == '1.0.0'
    assert isinstance(metadata.json, dict)


@pytest.mark.network
def test_wheel_metadata_isolation(package_test_flit: str) -> None:
    if importlib.util.find_spec('flit_core'):
        pytest.xfail('flit_core is available -- we want it missing!')  # pragma: no cover

    metadata = build.util.project_wheel_metadata(package_test_flit)

    assert metadata['name'] == 'test_flit'
    assert metadata['version'] == '1.0.0'
    assert isinstance(metadata.json, dict)

    with pytest.raises(
        build.BuildBackendException,
        match=re.escape("Backend 'flit_core.buildapi' is not available."),
    ):
        build.util.project_wheel_metadata(package_test_flit, isolated=False)


@pytest.mark.network
def test_with_get_requires(package_test_metadata: str) -> None:
    metadata = build.util.project_wheel_metadata(package_test_metadata)

    # Setuptools < v69.0.3 (https://github.com/pypa/setuptools/pull/4159) normalized this to dashes
    assert metadata['name'].replace('-', '_') == 'test_metadata'
    assert metadata['version'] == '1.0.0'
    assert metadata['summary'] == 'hello!'
    assert isinstance(metadata.json, dict)


def test_project_wheel_metadata_installs_build_requires_fresh(mocker: pytest_mock.MockerFixture) -> None:
    env = mocker.MagicMock()
    env_cm = mocker.MagicMock()
    env_cm.__enter__.return_value = env
    env_cm.__exit__.return_value = False
    mocker.patch('build.util.DefaultIsolatedEnv', return_value=env_cm)

    builder = mocker.MagicMock()
    builder.build_system_requires = {'dep1'}
    builder.get_requires_for_build.return_value = {'dep2'}
    mocker.patch('build.util.ProjectBuilder.from_isolated_env', return_value=builder)
    metadata = unittest.mock.sentinel.metadata
    mocker.patch('build.util._project_wheel_metadata', return_value=metadata)

    assert build.util.project_wheel_metadata('/tmp/project') is metadata

    assert env.install.call_args_list == [
        mocker.call({'dep1'}, _fresh=True),
        mocker.call({'dep2'}),
    ]


def test_merge_requirements_merges_by_canonical_name() -> None:
    collected = build.util._merge_requirements(
        ['Foo[extra]; python_version < "3.13"', 'bar'],
        ['foo >= 2; os_name == "nt"', 'Baz'],
    )

    by_name = {requirement.name: requirement for requirement in collected}
    assert set(by_name) == {'foo', 'bar', 'baz'}

    # merged by canonicalized name, sources recorded, PEP 508 strings preserved
    assert by_name['foo'].sources == {'static', 'dynamic'}
    assert by_name['foo'].requirements == ('Foo[extra]; python_version < "3.13"', 'foo >= 2; os_name == "nt"')
    assert by_name['bar'].sources == {'static'}
    assert by_name['bar'].requirements == ('bar',)
    assert by_name['baz'].sources == {'dynamic'}
    assert by_name['baz'].requirements == ('Baz',)


def test_merge_requirements_invalid_reports_indices() -> None:
    with pytest.raises(build.InvalidRequirementsError) as exc_info:
        build.util._merge_requirements(['ok-dep', 'bad dep'], ['fine-dep', 'also bad'])

    errors = exc_info.value.errors
    assert [(error.source, error.index) for error in errors] == [('static', 1), ('dynamic', 1)]
    assert errors[0].requirement == 'bad dep'
    assert errors[1].requirement == 'also bad'
    assert 'static[1]' in str(exc_info.value)
    assert 'dynamic[1]' in str(exc_info.value)


def test_collect_requirements_merges_static_and_dynamic(package_test_collect_requirements: str) -> None:
    hook_calls = []

    def counting_runner(cmd: list[str], cwd: str | None = None, extra_environ: dict[str, str] | None = None) -> None:
        hook_calls.append(cmd)
        pyproject_hooks.quiet_subprocess_runner(cmd, cwd, extra_environ)

    collected = build.util.collect_requirements(package_test_collect_requirements, runner=counting_runner)

    # the get_requires_for_build hook is called exactly once
    get_requires_calls = [cmd for cmd in hook_calls if any(str(part).startswith('get_requires_for_build') for part in cmd)]
    assert len(get_requires_calls) == 1

    by_name = {requirement.name: requirement for requirement in collected}
    assert set(by_name) == {'static-dep', 'shared-dep', 'dynamic-dep'}

    # statically and dynamically declared, merged by canonicalized name
    shared = by_name['shared-dep']
    assert shared.sources == {'static', 'dynamic'}
    assert shared.requirements == ('shared-dep; python_version >= "3.10"', 'Shared_Dep < 3')

    assert by_name['static-dep'].sources == {'static'}
    assert by_name['static-dep'].requirements == ('static-dep',)
    assert by_name['dynamic-dep'].sources == {'dynamic'}
    assert by_name['dynamic-dep'].requirements == ('dynamic-dep >= 1.0',)


def test_collect_requirements_sdist_uses_sdist_hook(package_test_collect_requirements: str) -> None:
    collected = build.util.collect_requirements(
        package_test_collect_requirements, 'sdist', runner=pyproject_hooks.quiet_subprocess_runner
    )

    by_name = {requirement.name: requirement for requirement in collected}
    assert set(by_name) == {'static-dep', 'shared-dep', 'sdist-dep'}
    assert by_name['sdist-dep'].sources == {'dynamic'}


def test_collect_requirements_invalid(package_test_collect_requirements_invalid: str) -> None:
    with pytest.raises(build.InvalidRequirementsError) as exc_info:
        build.util.collect_requirements(
            package_test_collect_requirements_invalid, runner=pyproject_hooks.quiet_subprocess_runner
        )

    # no merged list is returned; offending declarations carry source and index
    errors = exc_info.value.errors
    assert [(error.source, error.index) for error in errors] == [('static', 1), ('dynamic', 1)]
    assert errors[0].requirement == 'this is invalid'
    assert errors[1].requirement == 'also not valid'
    message = str(exc_info.value)
    assert "static[1]: 'this is invalid'" in message
    assert "dynamic[1]: 'also not valid'" in message
