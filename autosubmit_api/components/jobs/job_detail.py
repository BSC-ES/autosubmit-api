from datetime import datetime
from typing import List, Optional

from autosubmit_api.builders.configuration_facade_builder import (
    AutosubmitConfigurationFacadeBuilder,
    ConfigurationFacadeDirector,
)
from autosubmit_api.repositories.experiment_run import (
    ExperimentRunModel,
    create_experiment_run_repository,
)
from autosubmit_api.repositories.job_data import (
    ExperimentJobDataModel,
    create_experiment_job_data_repository,
)
from autosubmit_api.repositories.job_packages import (
    JobPackageModel,
    create_job_packages_repository,
)
from autosubmit_api.repositories.jobs import JobData, create_jobs_repository


class JobNotFoundError(Exception):
    """Exception raised when a job is not found."""


class JobDetailRetriever:
    """
    Class to get the details of a single job.
    """

    def __init__(self, expid: str, job_name: str):
        self.expid = expid
        self.job_name = job_name

        self._job_data: Optional[JobData] = None
        self._run_data: Optional[ExperimentRunModel] = None
        self._historical_data: Optional[ExperimentJobDataModel] = None
        self._config_facade = None
        self._wrapper_data: List[JobPackageModel] = []

        self.warnings = []

    def load_data(self):
        self._load_base_job_data()
        self._load_experiment_run_data()
        self._load_historical_job_last_data()
        self._load_config_files_data()
        self._load_wrapper_data()

    def _load_base_job_data(self):
        job_list_repo = create_jobs_repository(self.expid)
        self._job_data = job_list_repo.get_by_name(self.job_name)
        if not self._job_data:
            raise JobNotFoundError()

    def _load_experiment_run_data(self):
        try:
            run_repo = create_experiment_run_repository(self.expid)
            self._run_data = run_repo.get_last_run()
        except Exception as exc:
            self.warnings.append(
                {"message": "Failed to load experiment run data", "exception": str(exc)}
            )

    def _load_historical_job_last_data(self):
        try:
            job_data_repo = create_experiment_job_data_repository(self.expid)
            self._historical_data = job_data_repo.get_last_job_data_by_name(
                self.job_name
            )
        except Exception as exc:
            self.warnings.append(
                {"message": "Failed to load historical job data", "exception": str(exc)}
            )

    def _load_config_files_data(self):
        try:
            autosubmit_config_facade = ConfigurationFacadeDirector(
                AutosubmitConfigurationFacadeBuilder(self.expid)
            ).build_autosubmit_configuration_facade()
            self._config_facade = autosubmit_config_facade
        except Exception as exc:
            self.warnings.append(
                {"message": "Failed to load config files data", "exception": str(exc)}
            )

    def _load_wrapper_data(self):
        try:
            job_package_repo = create_job_packages_repository(self.expid)
            job_packages = job_package_repo.get_by_job_name(self.job_name)
            if not job_packages:
                job_package_repo = create_job_packages_repository(
                    self.expid, wrapper=True
                )
                job_packages = job_package_repo.get_by_job_name(self.job_name)
            self._wrapper_data = job_packages
        except Exception as exc:
            self.warnings.append(
                {"message": "Failed to load job package data", "exception": str(exc)}
            )

    @property
    def name(self) -> str:
        return self.job_name

    @property
    def status_code(self) -> Optional[int]:
        return self._job_data.status

    @property
    def section(self) -> Optional[str]:
        return self._job_data.section

    @property
    def date(self) -> Optional[datetime]:
        return self._job_data.date

    @property
    def member(self) -> Optional[str]:
        return self._job_data.member

    @property
    def chunk(self) -> Optional[int]:
        return self._job_data.chunk

    @property
    def chunk_size(self) -> Optional[int]:
        if self._config_facade and self._config_facade.chunk_size is not None:
            return self._config_facade.chunk_size
        elif self._run_data and self._run_data.chunk_size is not None:
            return self._run_data.chunk_size
        return None

    @property
    def chunk_unit(self) -> Optional[str]:
        if self._config_facade and self._config_facade.chunk_unit is not None:
            return self._config_facade.chunk_unit
        elif self._run_data and self._run_data.chunk_unit is not None:
            return self._run_data.chunk_unit
        return None

    @property
    def platform(self) -> Optional[str]:
        section_platform = (
            self._config_facade.get_section_platform(self.section)
            if self._config_facade
            else None
        )
        if section_platform is not None:
            return section_platform
        elif self._historical_data and self._historical_data.platform is not None:
            return self._historical_data.platform
        return None

    @property
    def remote_id(self) -> Optional[str]:
        return self._historical_data.job_id if self._historical_data else None

    @property
    def qos(self) -> Optional[str]:
        section_qos = (
            self._config_facade.get_section_qos(self.section)
            if self._config_facade
            else None
        )
        if section_qos is not None:
            return section_qos
        elif self._historical_data and self._historical_data.qos is not None:
            return self._historical_data.qos
        return None

    @property
    def processors(self) -> Optional[int]:
        section_processors = (
            self._config_facade.get_section_processors(self.section)
            if self._config_facade
            else None
        )
        if section_processors is not None:
            return section_processors
        elif self._historical_data and self._historical_data.ncpus is not None:
            return self._historical_data.ncpus
        return None

    @property
    def wallclock(self) -> Optional[str]:
        section_wallclock = (
            self._config_facade.get_section_wallclock(self.section)
            if self._config_facade
            else None
        )
        if section_wallclock is not None:
            return section_wallclock
        elif self._historical_data and self._historical_data.wallclock is not None:
            return self._historical_data.wallclock
        return None

    @property
    def workflow_commit(self) -> Optional[str]:
        config_workflow_commit = (
            self._config_facade.get_workflow_commit() if self._config_facade else None
        )
        if config_workflow_commit is not None:
            return config_workflow_commit
        elif (
            self._historical_data and self._historical_data.workflow_commit is not None
        ):
            return self._historical_data.workflow_commit
        return None

    @property
    def last_wrapper(self) -> Optional[str]:
        if self._wrapper_data:
            return self._wrapper_data[-1].package_name
        return None
