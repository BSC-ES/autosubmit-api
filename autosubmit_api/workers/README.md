These scripts are currently called from the `crontab`, but you can also execute them manually. 

* **populate_details_db**: This worker is in charge of populating the `details` table in the autosubmit database `ecearth.db`.
* **populate_graph**: This worker is in charge of finding active experiments and calculating the coordinates of their graph drawing. In the current setup, it is executed two times a day. It uses `portalocker` to avoid calculating the drawing of an experiment while a calculation is still going on, since `graphviz` can take hours in some cases. You might want to review the process and tune some parameters to optimize it.
* **populate_queue_run_times**; This worker goes through all the Autosubmit experiments and stores data about their jobs. This information represents a snapshot of the current status of the experiments under Autosubmit. It is in incremental update. We use this information as a backup source when the experiment database is not available.
* **populate_running_experiments**: This worker goes through all Autosubmit experiments, detects those that are active, and updates accordingly in the corresponding database. Sometimes an experiment can fail to set itself as `ACTIVE`, so this is a backup process that makes sure that the information is correct.
* **test_esarchive**: Worker that retrieves the information about the status of esarchive.
* **verify_complete**: This worker makes sure that the information collected by **populate_queue_run_times** is correct for the jobs completed in the last 30 minutes. This is a safety procedure.

Recommendations: Most of these scripts call procedures from other modules of the project. I'd be better if the specific procedures are all under this module. For example, **populate_graph** has its main logic under the `business` folder.
