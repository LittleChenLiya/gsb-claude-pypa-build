# SPDX-License-Identifier: MIT

import os


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    with open(os.path.join(wheel_directory, 'not a wheel'), 'wb') as f:
        f.write(b'not a wheel')
    return 'not a wheel'
