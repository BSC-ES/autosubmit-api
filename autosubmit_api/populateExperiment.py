#!/usr/bin/env python

import autosubmitAPIwu.experiment.common_requests as ExperimentUtils
import sys
from os.path import expanduser
from os.path import join
import getopt


def call_generate(experiment_path, job_path):
    home = expanduser("~")
    ExperimentUtils.generate_all_experiment_data(
        join(home, experiment_path), join(home, job_path))


def omain(argv):
    experiment_target = ''
    job_target = ''
    try:
        opts, args = getopt.getopt(argv, "he:j:", ["oexperiment=", "ojob="])
    except getopt.GetoptError:
        print('populateExperiment.py -e <experiment_file> -j <job_file> #')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('populateExperiment.py -e <experiment_file> -j <job_file>')
            sys.exit()
        elif opt in ("-e", "--oexperiment"):
            experiment_target = arg
        elif opt in ("-j", "--ojob"):
            job_target = arg
    #print("Experiment file is " + str(experiment_target))
    #print("Job file is " + str(job_target))
    call_generate(experiment_target, job_target)


if __name__ == "__main__":
    omain(sys.argv[1:])
