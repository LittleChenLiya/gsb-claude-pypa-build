# SPDX-License-Identifier: MIT


def get_requires_for_build_wheel(config_settings=None):
    return ['valid-dynamic-dep', 'also not valid']


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    raise NotImplementedError


def build_sdist(sdist_directory, config_settings=None):
    raise NotImplementedError
