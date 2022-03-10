# import autosubmitAPIwu.experiment.common_requests as ExperimentUtils
from autosubmit_api.history.experiment_status_manager import ExperimentStatusManager


def main():
    """
    Updates STATUS of experiments.
    """
    ExperimentStatusManager().update_running_experiments()


if __name__ == "__main__":
    main()
