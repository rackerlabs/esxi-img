import logging

try:
    import yaml
except ImportError:
    yaml = None

from esxi_netinit.configdata import ConfigData

logger = logging.getLogger(__name__)


class UserData:
    """Represents user_data."""

    def __init__(self, data: dict) -> None:
        self.configdata = ConfigData(**data)

    @staticmethod
    def from_yaml_file(path) -> "UserData":
        data = dict()
        if yaml:
            with open(path) as f:
                data.update(yaml.safe_load(f))
        return UserData(data)
