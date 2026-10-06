"""Fake build backend returning dynamic requirements and recording hook calls."""

import os


def _record_hook_call(hook_name):
    count_file = os.environ.get('BUILD_TEST_HOOK_COUNT_FILE')
    if count_file:
        with open(count_file, 'a', encoding='utf-8') as f:
            f.write(hook_name + '\n')


def get_requires_for_build_wheel(config_settings=None):
    _record_hook_call('get_requires_for_build_wheel')
    return [
        'shared-pkg >= 2.0; python_version < "3.99"',
        'dynamic-only-dep[extra] ~= 1.2',
    ]


def get_requires_for_build_sdist(config_settings=None):
    _record_hook_call('get_requires_for_build_sdist')
    return ['shared-pkg >= 2.0']
