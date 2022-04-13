`BasicConfig` provides a way to access the main configuration of the `API` (from `.autosubmitrc`). Make sure to execute `read()` before accesing the configuration information.

Inside `config_commong.py` you can find `AutosubmitConfig`. You can get the experiment configuration from this class; however, it is recommended that you use the `Autosubmit Configuration Facade` class to get this information.
