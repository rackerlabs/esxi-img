import logging
from functools import cached_property
from ipaddress import ip_network

from .esxhost import ESXHost
from .meta_data import MetaDataData
from .network import Network
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
        self.uplink_map = {}
        self.next_switch_number = 31

    def configure_hostname(self):
        self.host.set_hostname(self.meta_data.metadata.hostname)

    def clean_default_network_setup(self, portgroup_name, switch_name):
        """Removes default networking setup left by the installer."""
        self.host.delete_vmknic(portgroup_name=portgroup_name)
        self.host.portgroup_remove(
            switch_name=switch_name, portgroup_name=portgroup_name
        )
        self.host.destroy_vswitch(name=switch_name)

    def configure_default_route(self):
        """Configures default route.

        If multiple default routes are present, only first one is used.
        """
        route = self.network_data.default_route()
        self.host.configure_static_route(route.gateway, "default")

    def configure_static_routes(self):
        """Configures any static routes in the config."""
        for net in self.network_data.networks:
            for route in [r for r in net.routes if not r.is_default()]:
                route_net = ip_network(f"{route.network}/{route.netmask}")
                self.host.configure_static_route(route.gateway, route_net.compressed)

    def get_next_vswitch(self):
        switch_name = f"vSwitch{self.next_switch_number}"
        self.next_switch_number += 1
        return switch_name

    def configure_interface(self, net: Network, switch_name=None, portgroup_name=None):
        uplinks = self.identify_uplinks(net)
        if not uplinks:
            raise ValueError(f"No uplinks identified for network ID {net.network_id}")
        uplink_set = frozenset(u.name for u in uplinks)
        if uplink_set not in self.uplink_map:
            switch_name = switch_name or self.get_next_vswitch()
            self.configure_vswitch(switch_name, mtu=net.link.mtu, uplinks=uplinks)
            self.uplink_map[uplink_set] = switch_name
        else:
            switch_name = self.uplink_map[uplink_set]

        if not portgroup_name:
            if net.link.type == "vlan":
                portgroup_name = f"internal_net_vid_{net.link.vlan_id}"
            else:
                portgroup_name = net.link.id
        self.host.portgroup_add(portgroup_name, switch_name)
        if net.link.type == "vlan":
            self.host.portgroup_set_vlan(portgroup_name, net.link.vlan_id)

        mac = (
            "auto" if net.link.type == "vlan" else net.link.ethernet_mac_address.lower()
        )
        logger.info(
            "Creating %s with MAC %s for network %s", net.id, mac, net.network_id
        )
        self.host.add_ip_interface(net.id, portgroup_name, mac, net.link.mtu)

        if net.type == "ipv4":
            self.host.set_static_ipv4(net.id, net.ip_address, net.netmask)
        elif net.type == "ipv4_dhcp":
            self.host.set_dhcp_ipv4(net.id)
        else:
            raise NotImplementedError(f"net type {net.type}")

    def configure_vswitch(self, switch_name: str, mtu: int, uplinks: list[NIC]):
        """Sets up vSwitch."""
        logger.info("Creating vswitch %s with uplinks %s", switch_name, uplinks)
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

    def identify_uplinks(self, net: Network) -> list[NIC]:
        # Right now, a network can only refer to a single link, which will be either
        # a vlan (that then refers to an underlying link), or a direct link.
        # If at some point a new link type is defined that ties together multiple
        # underlying links in a team, that could result in multiple uplinks being
        # available to a network. Until then, there can only be a single result.
        if net.link.vlan_link:
            links = [net.link.vlan_link]
        else:
            links = [net.link]

        return [self.nics.find_by_mac(link.ethernet_mac_address) for link in links]

    @cached_property
    def nics(self):
        return NICList()

    @cached_property
    def management_network(self) -> Network:
        """Returns the network selected to be the management network.

        This will be first network with a default route defined, or the first
        network if no networks have a default route.
        """
        try:
            return next(
                (net for net in self.network_data.networks if net.default_routes()),
                next(iter(self.network_data.networks)),
            )
        except StopIteration:
            raise Exception("No candidate found for management network") from None

    @cached_property
    def other_networks(self) -> list[Network]:
        return [
            net
            for net in self.network_data.networks
            if net.id != self.management_network.id
        ]
