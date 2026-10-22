import os
import pwd
import subprocess
from unittest.mock import PropertyMock, patch

from autosubmit_api.components.experiment.file_metadata import FileMetadata


class TestFileMetadataOwnerName:
    def test_owner_name_matches_id_command(self, tmp_path):
        file_metadata = FileMetadata(tmp_path)

        expected = subprocess.run(
            ["id", "-nu", str(file_metadata.owner_id)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        assert file_metadata.owner_name == expected

    def test_owner_name_does_not_spawn_a_process(self, tmp_path):
        file_metadata = FileMetadata(tmp_path)

        with patch("os.popen", autospec=True, wraps=os.popen) as mock_popen:
            owner_name = file_metadata.owner_name

        assert owner_name == pwd.getpwuid(os.getuid()).pw_name
        mock_popen.assert_not_called()

    def test_owner_name_of_unknown_uid_is_empty(self, tmp_path):
        unknown_uid = max(entry.pw_uid for entry in pwd.getpwall()) + 1

        with patch.object(
            FileMetadata,
            "owner_id",
            new_callable=PropertyMock,
            return_value=unknown_uid,
        ):
            assert FileMetadata(tmp_path).owner_name == ""
