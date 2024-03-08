from typing import List, Union
import pickle
from networkx import DiGraph
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database.models import PklJobModel
from autosubmit_api.persistance.experiment import ExperimentPaths


class PklReader:

    def __init__(self, expid: str) -> None:
        self.expid = expid
        APIBasicConfig.read()
        self.pkl_path = ExperimentPaths(expid).job_list_pkl

    def read_pkl(self) -> Union[List, DiGraph]:
        with open(self.pkl_path, "rb") as f:
            return pickle.load(f, encoding="latin1")

    def parse_job_list(self) -> List[PklJobModel]:
        job_list = []
        obj = self.read_pkl()

        if isinstance(obj, DiGraph):
            for node in obj.nodes(data=True):
                job_content = node[1]["job"]
                jobpkl = PklJobModel(
                    name=job_content.name,
                    id=job_content.id,
                    status=job_content.status,
                    priority=job_content.priority,
                    section=job_content.section,
                    date=job_content.date,
                    member=job_content.member,
                    chunk=job_content.chunk,
                    out_path_local=job_content.local_logs[0],
                    err_path_local=job_content.local_logs[1],
                    out_path_remote=job_content.remote_logs[0],
                    err_path_remote=job_content.remote_logs[1],
                    wrapper_type=job_content.wrapper_type,
                )
                job_list.append(jobpkl)
        else:
            for item in obj:
                jobpkl = PklJobModel(
                    name=item[0],
                    id=item[1],
                    status=item[2],
                    priority=item[3],
                    section=item[4],
                    date=item[5],
                    member=item[6],
                    chunk=item[7],
                    out_path_local=item[8],
                    err_path_local=item[9],
                    out_path_remote=item[10],
                    err_path_remote=item[11],
                    wrapper_type=(item[12] if len(item) > 12 else None),
                )
                job_list.append(jobpkl)

        return job_list
