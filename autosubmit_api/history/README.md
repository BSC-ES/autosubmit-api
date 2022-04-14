Current and valid implementation of the `historical` module.

* **data_classes**: This folder contains the data classes that we reference when dealing with the historical module. Here we find the `Job Data` class that is the representation of the data of a job executed in the experiment, and `Experiment Run` that represents the run of an experiment. These are database models with some important logic added to them. Ideally, the logic should be separated from the data model, but it was added to the model for simplicity. In the future, consider separating the logic into another class.
* **database_managers**: Contains the `Database Manager` abstract class that should be the base for any other class dealing with databases in the project. Currently, that is not the case. At first, we considered using `SQLAlchemy` as a database manager, but conflicting dependencies in `Python 2.7` didn't allow for that. Then, we have `Experiment History Db Manager` and `Experiment Status Db Manager`, these implementations of the `Database Manager` deal with the necessary logic for the history module in the former case, and the experiment status update process in the latter. 
* **platform_monitor**: This folder contains the necessary classes to handle the output from the `sacct` command.
* **experiment_history**: Main logic of the `historical` module.
* **experiment_status**: Main logic of the experiment status update process at the experiment level.
* **experiment_status_manager**: Main logic of the experiment status process at the Autosubmit level (all experiments).
* **internal_logging**: Defines the classes of the internal log of the `historical` module.
* **strategies**: Defines the classes of the procedure that distributes the energy values retrieved from `sacct` into the jobs of a wrapper or a single job.
