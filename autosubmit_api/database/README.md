This package aims to encapsulate everything related to structured DDBB (SQLite/Postgres) operations.

* **common.py**: This module have all the common functions to allow DDBB interaction.

* **tables.py**: Holds all the table schemas. This module extends `autosubmit.tables`.

* **models.py**: Holds data validators. Might be refactored in the future.

* **table_manager.py**: Provides a generalized interface to interact with one table at the time.

* **adapters**: This subpackage holds all the entities and their corresponding operations. It should provide an interface for other parts of the API that prevents them to worry about DDBB logic.

