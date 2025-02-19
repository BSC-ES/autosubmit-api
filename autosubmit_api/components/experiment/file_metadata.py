import os
from pathlib import Path
from typing import Union

from autosubmit_api.common.utils import timestamp_to_datetime_format


class FileMetadata:
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self.stat = self.path.stat()

    @property
    def owner_id(self) -> int:
        return int(self.stat.st_uid)

    @property
    def owner_name(self) -> str:
        try:
            stdout = os.popen("id -nu {0}".format(str(self.owner_id)))
            owner_name = stdout.read().strip()
            return str(owner_name)
        except Exception:
            raise Exception("Error while getting owner name")

    @property
    def access_time(self) -> str:
        return timestamp_to_datetime_format(int(self.stat.st_atime))

    @property
    def modified_time(self) -> str:
        return timestamp_to_datetime_format(int(self.stat.st_mtime))

    @property
    def created_time(self) -> str:
        return timestamp_to_datetime_format(int(self.stat.st_ctime))
