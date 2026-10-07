"""Read-only probe of a PEP 517 backend's available hooks.

This is invoked in a subprocess, with the very same contract as
``pyproject_hooks``' in-process script, so that the backend is imported
exactly the way it is for a real hook call:

- Command line argument: control_dir
- Environment variables:
      _PYPROJECT_HOOKS_BUILD_BACKEND=entry.point:spec
      _PYPROJECT_HOOKS_BACKEND_PATH_JSON=paths (JSON encoded; optional)
- Result written to control_dir/output.json

Unlike a real hook call, no build hook is ever invoked -- the backend module
is merely imported and its attributes inspected -- so a capability query can
never trigger a build or cause the backend to write any output.
"""

from __future__ import annotations

import json
import os
import sys
import traceback

from importlib import import_module
from importlib.machinery import PathFinder


# PEP 517 (sdist/wheel) and PEP 660 (editable) backend hooks.
HOOK_NAMES = (
    'get_requires_for_build_sdist',
    'build_sdist',
    'get_requires_for_build_wheel',
    'prepare_metadata_for_build_wheel',
    'build_wheel',
    'get_requires_for_build_editable',
    'prepare_metadata_for_build_editable',
    'build_editable',
)


class BackendUnavailable(Exception):
    """Raised if the backend cannot be imported."""

    def __init__(self, message: str, tb: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.traceback = tb


def _write_json(obj: dict[str, object], path: str) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f)


class _BackendPathFinder:
    """Locate top-level backend modules in ``backend-path`` (per PEP 517)."""

    def __init__(self, backend_path: list[str], backend_module: str) -> None:
        self.backend_path = backend_path
        self.backend_parent, _, _ = backend_module.partition('.')

    def find_spec(self, fullname: str, _path: object, _target: object = None) -> object:
        if '.' in fullname:
            # Rely on importlib to find nested modules based on parent's path
            return None
        spec = PathFinder.find_spec(fullname, path=self.backend_path)
        if spec is None and fullname == self.backend_parent:
            msg = f'Cannot find module {self.backend_parent!r} in {self.backend_path!r}'
            raise BackendUnavailable(msg)
        return spec


def _build_backend() -> object:
    """Find and import the build backend, honoring ``backend-path``."""
    backend_path_json = os.environ.get('_PYPROJECT_HOOKS_BACKEND_PATH_JSON')
    ep = os.environ['_PYPROJECT_HOOKS_BUILD_BACKEND']
    mod_path, _, obj_path = ep.partition(':')

    extra_pathitems = json.loads(backend_path_json) if backend_path_json else []
    if extra_pathitems:
        # In-tree backend directories must take precedence on import.
        sys.meta_path.insert(0, _BackendPathFinder(extra_pathitems, mod_path))

    try:
        obj: object = import_module(mod_path)
    except ImportError:
        msg = f'Cannot import {mod_path!r}'
        raise BackendUnavailable(msg, traceback.format_exc()) from None

    if obj_path:
        for path_part in obj_path.split('.'):
            if not hasattr(obj, path_part):
                msg = f'Cannot find attribute {path_part!r} in backend {mod_path!r}'
                raise BackendUnavailable(msg, traceback.format_exc()) from None
            obj = getattr(obj, path_part)
    return obj


def _probe() -> list[str]:
    backend = _build_backend()
    # ``hasattr`` is exactly how pyproject_hooks decides that an optional hook
    # is missing; merely resolving attributes never invokes a hook.
    return [hook for hook in HOOK_NAMES if hasattr(backend, hook)]


def main() -> None:
    if len(sys.argv) != 2:  # pragma: no cover - defensive CLI misuse
        sys.exit('Needs args: control_dir')
    control_dir = sys.argv[1]
    out_path = os.path.join(control_dir, 'output.json')

    # Do not let this script's directory leak into the backend's import path.
    here = os.path.normcase(os.path.realpath(os.path.dirname(__file__)))
    sys.path[:] = [path for path in sys.path if os.path.normcase(os.path.realpath(path)) != here]

    try:
        hooks = _probe()
    except BackendUnavailable as e:
        _write_json(
            {'no_backend': True, 'backend_error': e.message, 'traceback': e.traceback or ''},
            out_path,
        )
    else:
        _write_json({'hooks': hooks}, out_path)


if __name__ == '__main__':
    main()
