# SPDX-License-Identifier: MIT

"""
A tiny local build backend used to test build artifact path admission.

It always writes a real minimal wheel into the wheel directory, but the
returned path can be steered via the ``return-name`` config setting to
emulate a misbehaving/malicious backend (e.g. returning ``../old.whl`` or
the name of a symlink pointing outside the output directory).
"""

import os

from zipfile import ZipFile


NAME = 'test_path_escape'
VERSION = '1.0.0'
WHEEL_NAME = f'{NAME}-{VERSION}-py3-none-any.whl'
DIST_INFO = f'{NAME}-{VERSION}.dist-info'


def _write_wheel(wheel_directory):
    path = os.path.join(wheel_directory, WHEEL_NAME)
    with ZipFile(path, 'w') as zf:
        zf.writestr(f'{DIST_INFO}/METADATA', f'Metadata-Version: 2.1\nName: {NAME}\nVersion: {VERSION}\n')
        zf.writestr(f'{DIST_INFO}/WHEEL', 'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
        zf.writestr(f'{DIST_INFO}/RECORD', '')
    return WHEEL_NAME


def get_requires_for_build_wheel(config_settings=None):
    return []


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    _write_wheel(wheel_directory)
    if config_settings and 'return-name' in config_settings:
        return config_settings['return-name']
    return WHEEL_NAME
