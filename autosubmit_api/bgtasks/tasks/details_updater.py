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
        if not experiments:
            return 0

        details_repository = create_experiment_details_repository()
        stored_details = {
            detail.exp_id: detail for detail in details_repository.get_all()
        }

        # Read every experiment configuration before opening the write
        # transaction, so the database lock is not held during the reads.
        # Only the details that are missing or differ from the stored ones are written.
        changed_details = []
        for experiment in experiments:
            try:
                detail = cls._build_details_data_from_experiment(
                    experiment.id, experiment.name
                )
            except Exception as exc:
                cls.logger.error(
                    f"[{cls.id}] Error while processing experiment {experiment.name}: {exc}"
                )
                continue
            if stored_details.get(experiment.id) != detail:
                changed_details.append(detail)

        if not changed_details:
            return 0

        return details_repository.upsert_many_details(changed_details)

    @classmethod
    def _get_experiments(cls) -> list[ExperimentModel]:
        """
        Get the experiments list
        """
        experiment_repository = create_experiment_repository()
        return experiment_repository.get_all()

    @classmethod
    def _build_details_data_from_experiment(
        cls, exp_id: int, expid: str
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
