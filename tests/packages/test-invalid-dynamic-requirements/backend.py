"""Fake build backend returning a mix of valid and invalid dynamic requirements."""


def get_requires_for_build_wheel(config_settings=None):
    return [
        'valid-dynamic-dep',
        'also not valid !!!',
    ]
