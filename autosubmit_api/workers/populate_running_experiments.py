# import autosubmitAPIwu.experiment.common_requests as ExperimentUtils
from autosubmit_api.bgtasks.bgtask import PopulateRunningExperiments

def main():
    """
    Updates STATUS of experiments.
    """
    PopulateRunningExperiments.run()


if __name__ == "__main__":
    main()
