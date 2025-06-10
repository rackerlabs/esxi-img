import pytest

from esxi_netinit.esxconfig import ESXConfig
from esxi_netinit.esxhost import ESXHost
from esxi_netinit.network_data import NetworkData


@pytest.fixture
def host_mock(mocker):
    return mocker.Mock(spec=ESXHost)


def test_configure_requested_dns(host_mock, network_data_single):
    ndata = NetworkData(network_data_single)
    ec = ESXConfig(ndata, dry_run=False)
    ec.host = host_mock
    ec.configure_requested_dns()
    print(host_mock.configure_dns.call_args_list)
    host_mock.configure_dns.assert_called_once_with(servers=["8.8.4.4"])


def test_configure_default_route(network_data_single, host_mock):
    ndata = NetworkData(network_data_single)
    ec = ESXConfig(ndata, dry_run=False)
    ec.host = host_mock
    ec.configure_default_route()
    host_mock.configure_default_route.assert_called_once_with("192.168.1.1")


def test_configure_management_interface(network_data_single, host_mock):
    ndata = NetworkData(network_data_single)
    ec = ESXConfig(ndata, dry_run=False)
    ec.host = host_mock
    mgmt_pg = "Management Network"
    mgmt_net = ndata.networks[0]
    ec.configure_management_interface(mgmt_pg)
    host_mock.add_ip_interface.assert_called_once_with(
        mgmt_net.id, mgmt_pg, mgmt_net.link.ethernet_mac_address, mgmt_net.link.mtu
    )
    host_mock.set_static_ipv4.assert_called_once_with(
        mgmt_net.id, mgmt_net.ip_address, mgmt_net.netmask
    )


def test_configure_vlans(network_data_multi, host_mock):
    ndata = NetworkData(network_data_multi)
    ec = ESXConfig(ndata, dry_run=False)
    ec.host = host_mock
    ec.configure_vlans()
    assert host_mock.portgroup_add.call_count == 3
    assert host_mock.portgroup_set_vlan.call_count == 3
    host_mock.portgroup_set_vlan.assert_called_with(
        portgroup_name="internal_net_vid_444", vlan_id=444
    )
