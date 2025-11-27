import logging
import subprocess

logger = logging.getLogger(__name__)


class ESXHost:
    """Low level commands for configuring various aspects of ESXi hypervisor."""

    def __init__(self, dry_run=False) -> None:
        self.dry_run = dry_run

    def __execute(self, cmd: list):
        if self.dry_run:
            logger.info("Would execute: %s", " ".join(cmd))
            return cmd
        else:
            logger.debug("Executing %s", cmd)
            subprocess.run(cmd, check=True)  # noqa: S603

    def set_hostname(self, hostname: str):
        cmd = [
            "/bin/esxcli",
            "system",
            "hostname",
            "set",
            "--fqdn",
            hostname,
        ]
        return self.__execute(cmd)

    def add_ip_interface(self, inf: str, portgroup_name: str, mac: str, mtu: int):
        """Adds IP interface."""
        logger.info(
            "Adding IP interface %s (%s) for portgroup %s", inf, mac, portgroup_name
        )
        cmd = [
            "/bin/esxcli",
            "network",
            "ip",
            "interface",
            "add",
            "--interface-name",
            inf,
        ]
        if mac != "auto":
            cmd.extend(["--mac-address", mac])
        cmd.extend(
            [
                "--mtu",
                str(mtu),
                "--portgroup-name",
                portgroup_name,
            ]
        )
        return self.__execute(cmd)

    def configure_static_route(self, gateway, network):
        cmd = [
            "/bin/esxcli",
            "network",
            "ip",
            "route",
            "ipv4",
            "add",
            "-g",
            gateway,
            "-n",
            network,
        ]
        return self.__execute(cmd)

    def change_ip(self, interface, ip, netmask):
        """Configures IP address on logical interface."""
        cmd = [
            "/bin/esxcli",
            "network",
            "ip",
            "interface",
            "ipv4",
            "set",
            "-i",
            interface,
            "-I",
            ip,
            "-N",
            netmask,
            "-t",
            "static",
        ]
        return self.__execute(cmd)

    def set_dhcp_ipv4(self, inf: str):
        """Configures DHCP (IPv4) on an interface."""
        logger.info("Configuring IPv4 interface %s with DHCP", inf)
        cmd = [
            "/bin/esxcli",
            "network",
            "ip",
            "interface",
            "ipv4",
            "set",
            "--interface-name",
            inf,
            "--peer-dns=true",
            "--type=dhcp",
        ]
        return self.__execute(cmd)

    def set_static_ipv4(self, inf: str, ip_addr: str, netmask: str):
        """Configures a static IPv4 address on an interface."""
        logger.info("Configuring IPv4 interface %s with static IP %s", inf, ip_addr)
        cmd = [
            "/bin/esxcli",
            "network",
            "ip",
            "interface",
            "ipv4",
            "set",
            "--interface-name",
            inf,
            "--type=static",
            "--ipv4",
            ip_addr,
            "--netmask",
            netmask,
        ]
        return self.__execute(cmd)

    def configure_dns(self, servers=None, search=None):
        """Sets up arbitrary DNS servers."""
        if not servers:
            servers = []
        if not search:
            search = []

        for server in servers:
            self.__execute(
                [
                    "/bin/esxcli",
                    "network",
                    "ip",
                    "dns",
                    "server",
                    "add",
                    "--server",
                    server,
                ]
            )

        for domain in search:
            self.__execute(
                [
                    "/bin/esxcli",
                    "network",
                    "ip",
                    "dns",
                    "search",
                    "add",
                    "--domain",
                    domain,
                ]
            )

    def create_vswitch(self, name="vSwitch0", ports=256):
        """Creates vSwitch."""
        cmd = [
            "/bin/esxcli",
            "network",
            "vswitch",
            "standard",
            "add",
            "--ports",
            str(ports),
            "--vswitch-name",
            str(name),
        ]

        return self.__execute(cmd)

    def delete_vmknic(self, portgroup_name):
        """Deletes a vmknic from a portgroup."""
        return self.__execute(["/bin/esxcfg-vmknic", "-d", portgroup_name])

    def destroy_vswitch(self, name):
        cmd = [
            "/bin/esxcli",
            "network",
            "vswitch",
            "standard",
            "remove",
            "--vswitch-name",
            name,
        ]

        return self.__execute(cmd)

    def portgroup_add(self, portgroup_name, switch_name="vswitch0"):
        """Adds Portgroup to a vSwitch."""
        cmd = [
            "/bin/esxcli",
            "network",
            "vswitch",
            "standard",
            "portgroup",
            "add",
            "--portgroup-name",
            str(portgroup_name),
            "--vswitch-name",
            str(switch_name),
        ]
        return self.__execute(cmd)

    #
    def portgroup_remove(self, portgroup_name, switch_name):
        """Removes Portgroup from a vSwitch."""
        cmd = [
            "/bin/esxcli",
            "network",
            "vswitch",
            "standard",
            "portgroup",
            "remove",
            "--portgroup-name",
            str(portgroup_name),
            "--vswitch-name",
            str(switch_name),
        ]
        return self.__execute(cmd)

    def portgroup_set_vlan(self, portgroup_name, vlan_id):
        """Configures VLANid to be used on a portgroup."""
        cmd = [
            "/bin/esxcli",
            "network",
            "vswitch",
            "standard",
            "portgroup",
            "set",
            "--portgroup-name",
            str(portgroup_name),
            "--vlan-id",
            str(vlan_id),
        ]
        return self.__execute(cmd)

    def uplink_add(self, nic, switch_name="vSwitch0"):
        """Adds uplink to a vSwitch."""
        cmd = [
            "/bin/esxcli",
            "network",
            "vswitch",
            "standard",
            "uplink",
            "add",
            "--uplink-name",
            str(nic),
            "--vswitch-name",
            str(switch_name),
        ]
        return self.__execute(cmd)

    def vswitch_settings(self, mtu=9000, cdp="listen", name="vSwitch0"):
        cmd = [
            "/bin/esxcli",
            "network",
            "vswitch",
            "standard",
            "set",
            "--mtu",
            str(mtu),
            "--cdp-status",
            cdp,
            "--vswitch-name",
            str(name),
        ]
        return self.__execute(cmd)

    def vswitch_failover_uplinks(
        self, active_uplinks=None, standby_uplinks=None, name="vSwitch0"
    ):
        cmd = [
            "/bin/esxcli",
            "network",
            "vswitch",
            "standard",
            "policy",
            "failover",
            "set",
        ]

        if active_uplinks:
            cmd.extend(["--active-uplinks", ",".join(active_uplinks)])
        if standby_uplinks:
            cmd.extend(["--standby-uplinks", ",".join(standby_uplinks)])

        cmd.extend(
            [
                "--vswitch-name",
                str(name),
            ]
        )
        return self.__execute(cmd)

    def vswitch_security(
        self,
        allow_forged_transmits="no",
        allow_mac_change="no",
        allow_promiscuous="no",
        name="vSwitch0",
    ):
        cmd = [
            "/bin/esxcli",
            "network",
            "vswitch",
            "standard",
            "policy",
            "security",
            "set",
            "--allow-forged-transmits",
            allow_forged_transmits,
            "--allow-mac-change",
            allow_mac_change,
            "--allow-promiscuous",
            allow_promiscuous,
            "--vswitch-name",
            str(name),
        ]
        return self.__execute(cmd)
