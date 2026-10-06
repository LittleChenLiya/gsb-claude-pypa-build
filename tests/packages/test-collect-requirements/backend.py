# SPDX-License-Identifier: MIT


def get_requires_for_build_wheel(config_settings=None):
    return ['dynamic-dep >= 1.0', 'Shared_Dep < 3']


def get_requires_for_build_sdist(config_settings=None):
    return ['sdist-dep']


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    raise NotImplementedError


def build_sdist(sdist_directory, config_settings=None):
    raise NotImplementedError
