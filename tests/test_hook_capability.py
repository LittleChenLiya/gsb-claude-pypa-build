# SPDX-License-Identifier: MIT

"""Local tests for the read-only PEP 517 hook-capability query.

The query reports which hooks a backend provides *without* ever invoking a
build hook, and a backend that fails to import is reported distinctly from one
that merely does not implement a hook. The existing
``prepare_metadata_for_build_wheel`` -> build-wheel fallback in
``ProjectBuilder.metadata_path`` continues to work and the caller can tell in
advance that the fallback will be used.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import textwrap

import pyproject_hooks
import pytest

import build


# Every hook checked by the capability query (PEP 517 + PEP 660).
ALL_HOOKS = {
    'get_requires_for_build_sdist',
    'build_sdist',
    'get_requires_for_build_wheel',
    'prepare_metadata_for_build_wheel',
    'build_wheel',
    'get_requires_for_build_editable',
    'prepare_metadata_for_build_editable',
    'build_editable',
}

PYPROJECT = textwrap.dedent(
    """\
    [build-system]
    requires = []
    build-backend = "{backend}"
    backend-path = ["."]
"""
)

# Backend with every PEP 517/660 hook. Every hook implementation logs its
# invocation to build-count.log so tests can prove the capability query and
# metadata preparation do not trigger a build.
FULL_BACKEND = textwrap.dedent(
    """\
    import os

    BUILD_COUNT_FILE = "build-count.log"

    def _count(hook):
        with open(BUILD_COUNT_FILE, "a", encoding="utf-8") as f:
            f.write(hook + "\\n")

    def get_requires_for_build_sdist(config_settings=None):
        _count("get_requires_for_build_sdist")
        return []

    def build_sdist(sdist_directory, config_settings=None):
        _count("build_sdist")
        name = "full-1.0.tar.gz"
        open(os.path.join(sdist_directory, name), "w").close()
        return name

    def get_requires_for_build_wheel(config_settings=None):
        _count("get_requires_for_build_wheel")
        return []

    def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
        _count("prepare_metadata_for_build_wheel")
        dist_info = os.path.join(metadata_directory, "full-1.0.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", encoding="utf-8") as f:
            f.write(
                "Metadata-Version: 2.2\\nName: full\\nVersion: 1.0\\n"
            )
        return "full-1.0.dist-info"

    def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
        _count("build_wheel")
        name = "full-1.0-py3-none-any.whl"
        open(os.path.join(wheel_directory, name), "w").close()
        return name

    def get_requires_for_build_editable(config_settings=None):
        _count("get_requires_for_build_editable")
        return []

    def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
        _count("prepare_metadata_for_build_editable")
        return "full-1.0.dist-info"

    def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
        _count("build_editable")
        name = "full-1.0-py3-none-any.whl"
        open(os.path.join(wheel_directory, name), "w").close()
        return name
"""
)

# Backend that only implements the mandatory sdist/wheel build hooks and no
# metadata hook (and no editable hooks).
NO_METADATA_BACKEND = textwrap.dedent(
    """\
    import os
    import zipfile

    def _count(hook):
        with open("build-count.log", "a", encoding="utf-8") as f:
            f.write(hook + "\\n")

    def build_sdist(sdist_directory, config_settings=None):
        _count("build_sdist")
        name = "nometa-1.0.tar.gz"
        open(os.path.join(sdist_directory, name), "w").close()
        return name

    def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
        _count("build_wheel")
        name = "nometa-1.0-py3-none-any.whl"
        with zipfile.ZipFile(os.path.join(wheel_directory, name), "w") as wheel:
            wheel.writestr("nometa/__init__.py", "")
            wheel.writestr(
                "nometa-1.0.dist-info/METADATA",
                "Metadata-Version: 2.2\\nName: nometa\\nVersion: 1.0\\n",
            )
        return name
"""
)

# Backend module that fails at import time.
BROKEN_BACKEND = "raise ImportError('deliberately broken backend')\n"


def _make_project(tmp_path: pathlib.Path, name: str, backend_module: str, backend_code: str) -> pathlib.Path:
    project = tmp_path / name
    project.mkdir()
    (project / 'pyproject.toml').write_text(PYPROJECT.format(backend=backend_module), encoding='utf-8')
    (project / f'{backend_module}.py').write_text(backend_code, encoding='utf-8')
    return project


def _build_count(project: pathlib.Path) -> list[str]:
    log = project / 'build-count.log'
    return log.read_text(encoding='utf-8').splitlines() if log.is_file() else []


@pytest.fixture
def full_project(tmp_path: pathlib.Path) -> pathlib.Path:
    return _make_project(tmp_path, 'full', 'full_backend', FULL_BACKEND)


@pytest.fixture
def no_metadata_project(tmp_path: pathlib.Path) -> pathlib.Path:
    return _make_project(tmp_path, 'nometa', 'no_metadata_backend', NO_METADATA_BACKEND)


@pytest.fixture
def broken_project(tmp_path: pathlib.Path) -> pathlib.Path:
    return _make_project(tmp_path, 'broken', 'broken_backend', BROKEN_BACKEND)


def test_capability_full_backend(full_project: pathlib.Path) -> None:
    builder = build.ProjectBuilder(full_project)

    assert builder.get_available_hooks() == ALL_HOOKS

    # The capability query is strictly read-only: no hook ran, no build output.
    assert _build_count(full_project) == []


def test_capability_no_metadata_hook(no_metadata_project: pathlib.Path) -> None:
    builder = build.ProjectBuilder(no_metadata_project)

    hooks = builder.get_available_hooks()

    # Importing the backend succeeds; only the unimplemented hooks are absent.
    assert hooks == {'build_sdist', 'build_wheel'}
    assert 'prepare_metadata_for_build_wheel' not in hooks
    assert _build_count(no_metadata_project) == []


def test_capability_backend_import_failure(broken_project: pathlib.Path) -> None:
    builder = build.ProjectBuilder(broken_project)

    # A missing backend is an import failure, not a missing hook: the query
    # raises the same wrapped BackendUnavailable other paths use.
    with pytest.raises(build.BuildBackendException) as exc_info:
        builder.get_available_hooks()
    assert isinstance(exc_info.value.exception, pyproject_hooks.BackendUnavailable)
    assert "Backend 'broken_backend' is not available." in str(exc_info.value)
    assert _build_count(broken_project) == []


def test_metadata_prepare_uses_direct_hook_without_build(full_project: pathlib.Path, tmp_path: pathlib.Path) -> None:
    builder = build.ProjectBuilder(full_project)

    # Caller can tell up-front the direct metadata hook will be used.
    assert 'prepare_metadata_for_build_wheel' in builder.get_available_hooks()
    assert _build_count(full_project) == []

    metadata_dir = builder.metadata_path(str(tmp_path / 'out'))

    assert os.path.basename(metadata_dir) == 'full-1.0.dist-info'
    # prepare_metadata_for_build_wheel ran; build_wheel never did.
    assert _build_count(full_project) == ['prepare_metadata_for_build_wheel']


def test_metadata_prepare_original_fallback_still_used(no_metadata_project: pathlib.Path, tmp_path: pathlib.Path) -> None:
    builder = build.ProjectBuilder(no_metadata_project)

    # The caller learns ahead of time that the fallback will be used.
    assert 'prepare_metadata_for_build_wheel' not in builder.get_available_hooks()
    assert _build_count(no_metadata_project) == []

    metadata_dir = builder.metadata_path(str(tmp_path / 'out'))

    assert os.path.basename(metadata_dir) == 'nometa-1.0.dist-info'
    # The pre-existing fallback: a wheel was built and metadata extracted.
    assert _build_count(no_metadata_project) == ['build_wheel']


def test_capability_invokes_runner_with_probe_contract(full_project: pathlib.Path) -> None:
    # No subprocess: emulate the probe writing its report, and assert the query
    # drives the configured runner with the pyproject_hooks env contract.
    def fake_runner(cmd: list[str], cwd: str, extra_environ: dict[str, str]) -> None:
        assert cmd[1].endswith(os.path.join('_in_process', '_probe_hooks.py'))
        assert cwd == str(full_project)
        assert extra_environ['_PYPROJECT_HOOKS_BUILD_BACKEND'] == 'full_backend'
        control_dir = cmd[2]
        with open(os.path.join(control_dir, 'output.json'), 'w', encoding='utf-8') as f:
            json.dump({'hooks': ['build_wheel']}, f)

    builder = build.ProjectBuilder(full_project, runner=fake_runner)

    assert builder.get_available_hooks() == {'build_wheel'}
    assert _build_count(full_project) == []


def test_capability_runner_failure_is_backend_exception(full_project: pathlib.Path) -> None:
    def failing_runner(cmd: list[str], _cwd: str, _extra_environ: dict[str, str]) -> None:
        raise subprocess.CalledProcessError(1, cmd)

    builder = build.ProjectBuilder(full_project, runner=failing_runner)

    with pytest.raises(build.BuildBackendException, match='Backend subprocess exited'):
        builder.get_available_hooks()
