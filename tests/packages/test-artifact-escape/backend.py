# SPDX-License-Identifier: MIT

import os
import zipfile


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    config_settings = config_settings or {}
    artifact = config_settings.get('artifact-name', 'test_artifact_escape-1.0.0-py3-none-any.whl')
    if config_settings.get('write-file', 'true') == 'true':
        with zipfile.ZipFile(os.path.join(wheel_directory, artifact), 'w') as whl:
            whl.writestr(
                'test_artifact_escape-1.0.0.dist-info/METADATA',
                'Metadata-Version: 2.1\nName: test-artifact-escape\nVersion: 1.0.0\n',
            )
    return artifact
