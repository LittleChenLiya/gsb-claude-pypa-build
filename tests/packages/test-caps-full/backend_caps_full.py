# SPDX-License-Identifier: MIT

import os
import os.path
import tarfile
import zipfile


_METADATA = 'Metadata-Version: 2.2\nName: test-caps-full\nVersion: 1.0.0\n'
_DISTINFO = 'test_caps_full-1.0.0.dist-info'


def _bump_counter():
    path = os.environ.get('BUILD_CAPS_COUNTER')
    if path is None:
        return
    count = 0
    if os.path.exists(path):
        with open(path, encoding='utf-8') as file:
            count = int(file.read())
    with open(path, 'w', encoding='utf-8') as file:
        file.write(str(count + 1))


def get_requires_for_build_sdist(config_settings=None):
    return []


def get_requires_for_build_wheel(config_settings=None):
    return []


def get_requires_for_build_editable(config_settings=None):
    return []


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    distinfo_dir = os.path.join(metadata_directory, _DISTINFO)
    os.makedirs(distinfo_dir, exist_ok=True)
    with open(os.path.join(distinfo_dir, 'METADATA'), 'w', encoding='utf-8') as file:
        file.write(_METADATA)
    return _DISTINFO


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    return prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def _make_wheel(wheel_directory):
    _bump_counter()
    basename = 'test_caps_full-1.0.0-py3-none-any.whl'
    with zipfile.ZipFile(os.path.join(wheel_directory, basename), 'w') as wheel:
        wheel.writestr(f'{_DISTINFO}/METADATA', _METADATA)
    return basename


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    return _make_wheel(wheel_directory)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    return _make_wheel(wheel_directory)


def build_sdist(sdist_directory, config_settings=None):
    _bump_counter()
    basename = 'test-caps-full-1.0.0.tar.gz'
    with tarfile.open(os.path.join(sdist_directory, basename), 'w:gz'):
        pass
    return basename
