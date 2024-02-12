# import autosubmitAPIwu.experiment.common_requests as ExperimentUtils
from autosubmit_api.bgtasks.tasks.status_updater import StatusUpdater

def main():
    """
    Updates STATUS of experiments.
    """
    StatusUpdater.run()


if __name__ == "__main__":
    main()
