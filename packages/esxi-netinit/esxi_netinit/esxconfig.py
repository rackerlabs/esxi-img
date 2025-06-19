import logging
from functools import cached_property

from .esxhost import ESXHost
from .meta_data import MetaDataData
from .network_data import NetworkData
from .nic import NIC
from .nic_list import NICList

logger = logging.getLogger(__name__)


class ESXConfig:
    def __init__(
        self, network_data: NetworkData, meta_data: MetaDataData, dry_run=False
    ) -> None:
        self.network_data = network_data
        self.meta_data = meta_data
        self.dry_run = dry_run
        self.host = ESXHost(dry_run)

    def configure_hostname(self):
        self.host.set_hostname(self.meta_data.metadata.hostname)

    def clean_default_network_setup(self, portgroup_name, switch_name):
        """Removes default networking setup left by the installer."""
        self.host.delete_vmknic(portgroup_name=portgroup_name)
        self.host.portgroup_remove(
            switch_name=switch_name, portgroup_name=portgroup_name
        )
        self.host.destroy_vswitch(name=switch_name)

    def configure_portgroups(self, switch_name: str, portgroups):
        """Adds each requested portgroup to the specified switch."""
        for portgroup_name in portgroups:
            self.host.portgroup_add(portgroup_name, switch_name)

    def configure_default_route(self):
        """Configures default route.

        If multiple default routes are present, only first one is used.
        """
        route = self.network_data.default_route()
        self.host.configure_default_route(route.gateway)

    def configure_vlans(self, switch_name="vSwitch0"):
        portgroups = []
        for link in self.network_data.links:
            if link.type == "vlan":
                vid = link.vlan_id
                pg_name = f"internal_net_vid_{vid}"
                self.host.portgroup_add(portgroup_name=pg_name, switch_name=switch_name)
                self.host.portgroup_set_vlan(portgroup_name=pg_name, vlan_id=vid)
                portgroups.append(pg_name)
        return portgroups

    def configure_management_interface(self, mgmt_portgroup: str):
        for net in self.network_data.networks:
            logger.info(
                "Creating %s with MAC %s for network %s",
                net.id,
                net.link.ethernet_mac_address,
                net.network_id,
            )
            self.host.add_ip_interface(
                net.id, mgmt_portgroup, net.link.ethernet_mac_address, net.link.mtu
            )
            if net.type == "ipv4":
                self.host.set_static_ipv4(net.id, net.ip_address, net.netmask)
            elif net.type == "ipv4_dhcp":
                self.host.set_dhcp_ipv4(net.id)
            else:
                raise NotImplementedError(f"net type {net.type}")

    def configure_vswitch(self, switch_name: str, mtu: int):
        """Sets up vSwitch."""
        uplinks: list[NIC] = self.identify_uplinks()

        self.host.create_vswitch(switch_name)
        for uplink in uplinks:
            self.host.uplink_add(nic=uplink.name, switch_name=switch_name)

        self.host.vswitch_failover_uplinks(
            active_uplinks=[uplink.name for uplink in uplinks], name=switch_name
        )

        self.host.vswitch_security(name=switch_name)
        self.host.vswitch_settings(mtu=mtu, name=switch_name)

    def configure_requested_dns(self):
        """Configures DNS servers that were provided in network_data.json."""
        dns_servers = [
            srv.address for srv in self.network_data.services if srv.type == "dns"
        ]
        if not dns_servers:
            return

        return self.host.configure_dns(servers=dns_servers)

    def identify_uplinks(self) -> list[NIC]:
        eligible_networks = [
            net for net in self.network_data.networks if net.default_routes()
        ]

        return [
            self.nics.find_by_mac(n.link.ethernet_mac_address)
            for n in eligible_networks
        ]

    @cached_property
    def nics(self):
        return NICList()
