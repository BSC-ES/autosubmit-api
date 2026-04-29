from typing import Optional, Union

from autosubmit_api.common.utils import get_processors_number
from autosubmit_api.components.jobs.utils import convert_int_default
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.config.config_common import AutosubmitConfigResolver
from bscearth.utils.config_parser import ConfigParserFactory

from autosubmit_api.config.ymlConfigStrategy import ymlConfigStrategy


class JobSectionConfiguration:
    def __init__(
        self,
        expid: str,
        section: str,
        basic_config: Optional[type[APIBasicConfig]] = None,
        as_conf: Optional[AutosubmitConfigResolver] = None,
    ):
        self.expid = expid
        self.section = section

        if isinstance(basic_config, APIBasicConfig):
            self.basic_config = basic_config
        else:
            self.basic_config = APIBasicConfig
            self.basic_config.read()

        if isinstance(as_conf, AutosubmitConfigResolver):
            self.as_conf = as_conf
        else:
            self.as_conf = AutosubmitConfigResolver(
                self.expid, self.basic_config, ConfigParserFactory()
            )
            self.as_conf.reload()

    @property
    def processors(self):
        return get_processors_number(self.as_conf.get_processors(self.section))

    @property
    def tasks(self) -> Union[int, None]:
        return convert_int_default(self.as_conf.get_tasks(self.section))

    @property
    def nodes(self) -> Union[int, None]:
        if isinstance(self.as_conf._configWrapper, ymlConfigStrategy):
            return convert_int_default(
                self.as_conf._configWrapper.get_nodes(self.section)
            )
        else:
            return None

    @property
    def processors_per_node(self) -> Union[int, None]:
        if isinstance(self.as_conf._configWrapper, ymlConfigStrategy):
            return convert_int_default(
                self.as_conf._configWrapper.get_processors_per_node(self.section)
            )
        else:
            return None

    @property
    def exclusive(self) -> bool:
        if isinstance(self.as_conf._configWrapper, ymlConfigStrategy):
            return self.as_conf._configWrapper.get_exclusive(self.section)
        else:
            return False
