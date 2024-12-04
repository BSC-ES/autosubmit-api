import tempfile
from pathlib import Path
import random
from autosubmit_api.experiment.utils import get_files_from_dir_with_pattern


def test_get_files_from_dir_with_pattern():
    N_VALID_FILES = 32
    N_INVALID_FILES = 8

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        # Create some test files with the pattern and write some content in random order
        file_paths = []
        random_list = list(range(N_VALID_FILES))
        random.shuffle(random_list)
        for i in random_list:
            file_path = temp_dir_path.joinpath(f"test_file_{i}")
            file_path.write_text(f"Valid file {i}")
            file_paths.append(file_path)

        # Create some files that do not match the pattern
        for i in range(N_INVALID_FILES):
            file_path = temp_dir_path.joinpath(f"other_file_{i}")
            file_path.write_text(f"Invalid file {i}")

        # Test the function with the pattern
        matching_files = get_files_from_dir_with_pattern(temp_dir, "test_file")
        assert len(matching_files) == N_VALID_FILES
        assert all("test_file" in file for file in matching_files)

        # Check is returned in descending order by modification time
        for i in range(1, N_VALID_FILES):
            assert (
                Path(temp_dir).joinpath(matching_files[i - 1]).stat().st_mtime
                >= Path(temp_dir).joinpath(matching_files[i]).stat().st_mtime
            )

        # Test with a pattern that does not match any file
        non_matching_files = get_files_from_dir_with_pattern(
            temp_dir, "non_existent_pattern"
        )
        assert len(non_matching_files) == 0
