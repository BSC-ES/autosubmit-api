from typing import List
from autosubmit_api.bgtasks.bgtask import BackgroundTaskTemplate
from autosubmit_api.builders.configuration_facade_builder import (
    AutosubmitConfigurationFacadeBuilder,
    ConfigurationFacadeDirector,
)
from autosubmit_api.repositories.experiment import (
    ExperimentModel,
    create_experiment_repository,
)
from autosubmit_api.repositories.experiment_details import (
    create_experiment_details_repository,
    ExperimentDetailsModel,
)


class PopulateDetailsDB(BackgroundTaskTemplate):
    id = "TASK_POPDET"
    trigger_options = {"trigger": "interval", "minutes": 240}

    @classmethod
    def procedure(cls):
        """
        Procedure to populate the details table
        """

        # Get experiments
        experiments = cls._get_experiments()

        rows_added = 0

        for experiment in experiments:
            try:
                # Get details data from the experiment
                details_data = cls._build_details_data_from_experiment(
                    experiment.id, experiment.name
                )

                # Insert details data into the details table
                rows_added += cls._upsert_details_data(details_data)
            except Exception as exc:
                cls.logger.error(
                    f"[{cls.id}] Error while processing experiment {experiment.name}: {exc}"
                )

        return rows_added

    @classmethod
    def _get_experiments(cls) -> List[ExperimentModel]:
        """
        Get the experiments list
        """
        experiment_repository = create_experiment_repository()
        return experiment_repository.get_all()

    @classmethod
    def _build_details_data_from_experiment(
        self, exp_id: int, expid: str
    ) -> ExperimentDetailsModel:
        """
        Build the details data from the experiment
        """
        autosubmit_config = ConfigurationFacadeDirector(
            AutosubmitConfigurationFacadeBuilder(expid)
        ).build_autosubmit_configuration_facade()
        return ExperimentDetailsModel(
            exp_id=exp_id,
            user=autosubmit_config.get_owner_name(),
            created=autosubmit_config.get_experiment_created_time_as_datetime(),
            model=autosubmit_config.get_model(),
            branch=autosubmit_config.get_branch(),
            hpc=autosubmit_config.get_main_platform(),
        )

    @classmethod
    def _upsert_details_data(cls, details_data: ExperimentDetailsModel):
        """
        Insert or update details data into the details table
        """
        details_repository = create_experiment_details_repository()
        return details_repository.upsert_details(
            details_data.exp_id,
            details_data.user,
            details_data.created,
            details_data.model,
            details_data.branch,
            details_data.hpc,
        )
