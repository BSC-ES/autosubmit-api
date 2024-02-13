import os
from autosubmit_api.config.basicConfig import APIBasicConfig


class ExperimentPaths:
    """
    Helper class that builds related directories/files paths of an experiment
    """

    def __init__(self, expid: str) -> None:
        self._expid = expid

    @property
    def expid(self):
        return self._expid

    @property
    def exp_dir(self):
        return os.path.join(APIBasicConfig.LOCAL_ROOT_DIR, self.expid)

    @property
    def pkl_dir(self):
        return os.path.join(self.exp_dir, "pkl")

    @property
    def job_list_pkl(self):
        filename = f"job_list_{self.expid}.pkl"
        return os.path.join(self.pkl_dir, filename)

    @property
    def job_packages_db(self):
        filename = f"job_packages_{self.expid}.db"
        return os.path.join(self.pkl_dir, filename)

    @property
    def tmp_dir(self):
        return os.path.join(self.exp_dir, APIBasicConfig.LOCAL_TMP_DIR)
    
    @property
    def tmp_dir(self):
        return os.path.join(self.exp_dir, APIBasicConfig.LOCAL_TMP_DIR)

    @property
    def tmp_log_dir(self):
        return os.path.join(self.tmp_dir, f"LOG_{self.expid}")