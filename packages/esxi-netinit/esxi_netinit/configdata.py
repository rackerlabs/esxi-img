from dataclasses import dataclass

from esxi_netinit.defaults import DEFAULT_PORTGROUP
from esxi_netinit.defaults import DEFAULT_VSWITCH


@dataclass
class ConfigData:
    configure_all_networks: bool = False
    management_vswitch: str = DEFAULT_VSWITCH
    management_portgroup: str = DEFAULT_PORTGROUP
    first_extra_vswitch_number: int = 1

    def __post_init__(self):
        """Pointless comment to appease the linter."""
        if self.first_extra_vswitch_number < 0:
            raise ValueError("first_extra_vswitch_number must be positive")
