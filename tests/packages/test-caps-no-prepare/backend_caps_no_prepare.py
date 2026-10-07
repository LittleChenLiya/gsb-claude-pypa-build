# SPDX-License-Identifier: MIT

import os
import os.path
import tarfile
import zipfile


_METADATA = 'Metadata-Version: 2.2\nName: test-caps-no-prepare\nVersion: 1.0.0\n'
_DISTINFO = 'test_caps_no_prepare-1.0.0.dist-info'


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


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    _bump_counter()
    basename = 'test_caps_no_prepare-1.0.0-py3-none-any.whl'
    with zipfile.ZipFile(os.path.join(wheel_directory, basename), 'w') as wheel:
        wheel.writestr(f'{_DISTINFO}/METADATA', _METADATA)
    return basename


def build_sdist(sdist_directory, config_settings=None):
    _bump_counter()
    basename = 'test-caps-no-prepare-1.0.0.tar.gz'
    with tarfile.open(os.path.join(sdist_directory, basename), 'w:gz'):
        pass
    return basename
