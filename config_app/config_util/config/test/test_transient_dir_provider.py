import pytest
import os

from config_app.config_util.config.TransientDirectoryProvider import TransientDirectoryProvider


@pytest.mark.parametrize(
    "files_to_write, operations, expected_new_dir",
    [
        pytest.param(
            {"config.yaml": "a config",},
            ([], [], []),
            {"config.yaml": "a config",},
            id="just a config",
        ),
        pytest.param(
            {"config.yaml": "a config", "oldfile": "hmmm"},
            ([], [], ["oldfile"]),
            {"config.yaml": "a config",},
            id="delete a file",
        ),
        pytest.param(
            {"config.yaml": "a config", "oldfile": "hmmm"},
            ([("newfile", "asdf")], [], ["oldfile"]),
            {"config.yaml": "a config", "newfile": "asdf"},
            id="delete and add a file",
        ),
        pytest.param(
            {"config.yaml": "a config", "somefile": "before"},
            ([("newfile", "asdf")], [("somefile", "after")], []),
            {"config.yaml": "a config", "newfile": "asdf", "somefile": "after",},
            id="add new files and change files",
        ),
    ],
)
def test_transient_dir_copy_config_dir(files_to_write, operations, expected_new_dir):
    config_provider = TransientDirectoryProvider("", "", "")

    for name, data in files_to_write.items():
        config_provider.write_volume_file(name, data)

    config_provider.create_copy_of_config_dir()

    for create in operations[0]:
        (name, data) = create
        config_provider.write_volume_file(name, data)

    for update in operations[1]:
        (name, data) = update
        config_provider.write_volume_file(name, data)

    for delete in operations[2]:
        config_provider.remove_volume_file(delete)

    # check that the new directory matches expected state
    for filename, data in expected_new_dir.items():
        with open(os.path.join(config_provider.get_config_dir_path(), filename)) as f:
            new_data = f.read()
            assert new_data == data

    # Now check that the old dir matches the original state
    saved = config_provider.get_old_config_dir()

    for filename, data in files_to_write.items():
        with open(os.path.join(saved, filename)) as f:
            new_data = f.read()
            assert new_data == data

    config_provider.temp_dir.cleanup()
