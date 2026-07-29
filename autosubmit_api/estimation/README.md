`calculate_eta` implements the ETA (Estimated Time of Arrival) computation for an experiment section running as chunk. It groups jobs by chunk, averages the runtime of completed chunks, and multiplies by the remaining incompleted chunks to estimate the time left.

The `ExperimentEtaService` in the `services` module orchestrates the ETA computation merging the current job list with historical data from the database before calling `calculate_eta`. This way we obtain the start time and end time of the last
run jobs in the experiment.
