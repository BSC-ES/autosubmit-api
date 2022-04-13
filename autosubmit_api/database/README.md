**db_common** contains some function to access Autosubmit database. It is mostly legacy code that needs to be restructured.

**db_jobdata** contains most of the classes of the old implementation of the `historical database`. It needs to be deleted, but some functions still use it. Replace the references to this old implementation for the new implementation `history` module and proceed to delete this file. Also, take out the `Graph Drawing` class.

**db_manager** is mostly legacy code that is still referenced.

**db_structure** handles the consumption of the structure database of the experiment.
