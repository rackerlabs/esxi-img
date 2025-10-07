import pytest

from esxi_netinit.esxconfig import ESXConfig
from esxi_netinit.esxhost import ESXHost
from esxi_netinit.meta_data import MetaDataData
from esxi_netinit.network_data import NetworkData
from esxi_netinit.nic import NIC


@pytest.fixture
def host_mock(mocker):
    return mocker.Mock(spec=ESXHost)


def test_configure_requested_dns(host_mock, network_data_single, meta_data):
    ndata = NetworkData(network_data_single)
    meta_data = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta_data, dry_run=False)
    ec.host = host_mock
    ec.configure_requested_dns()
    print(host_mock.configure_dns.call_args_list)
    host_mock.configure_dns.assert_called_once_with(servers=["8.8.4.4"])


def test_configure_default_route(network_data_single, meta_data, host_mock):
    ndata = NetworkData(network_data_single)
    meta_data = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta_data, dry_run=False)
    ec.host = host_mock
    ec.configure_default_route()
    host_mock.configure_default_route.assert_called_once_with("192.168.1.1")


def test_configure_management_interface(network_data_single, meta_data, host_mock):
    ndata = NetworkData(network_data_single)
    meta_data = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta_data, dry_run=False)
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


def test_configure_vlans(network_data_multi, meta_data, host_mock):
    ndata = NetworkData(network_data_multi)
    meta_data = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta_data, dry_run=False)
    ec.host = host_mock
    ec.configure_vlans()
    assert host_mock.portgroup_add.call_count == 3
    assert host_mock.portgroup_set_vlan.call_count == 3
    host_mock.portgroup_set_vlan.assert_called_with(
        portgroup_name="internal_net_vid_444", vlan_id=444
    )


def test_set_host_name(network_data_single, meta_data, host_mock):
    ndata = NetworkData(network_data_single)
    meta_data = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta_data, dry_run=False)
    ec.host = host_mock
    ec.configure_hostname()
    host_mock.set_hostname.assert_called_once_with("test.novalocal")


def test_configure_vswitch(mocker, network_data_single, meta_data, host_mock):
    ndata = NetworkData(network_data_single)
    meta = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta, dry_run=False)
    ec.host = host_mock

    uplinks = [
        NIC(name="vmnic0", status="Up", link="Up", mac="14:23:f3:f5:21:50"),
        NIC(name="vmnic1", status="Up", link="Up", mac="14:23:f3:f5:21:51"),
    ]

    mocker.patch.object(ec, "identify_uplinks", return_value=uplinks)

    ec.configure_vswitch("vSwitch42", mtu=9000)

    host_mock.create_vswitch.assert_called_once_with("vSwitch42")

    host_mock.uplink_add.assert_has_calls(
        [
            mocker.call(nic="vmnic0", switch_name="vSwitch42"),
            mocker.call(nic="vmnic1", switch_name="vSwitch42"),
        ]
    )
    assert host_mock.uplink_add.call_count == 2

    host_mock.vswitch_failover_uplinks.assert_called_once_with(
        active_uplinks=["vmnic0", "vmnic1"], name="vSwitch42"
    )
    host_mock.vswitch_security.assert_called_once_with(name="vSwitch42")
    host_mock.vswitch_settings.assert_called_once_with(mtu=9000, name="vSwitch42")


def test_identify_uplinks(network_data_single, meta_data, mocker):
    ndata = NetworkData(network_data_single)
    meta = MetaDataData(meta_data)

    mocker.patch("esxi_netinit.nic_list.NICList.__init__", return_value=None)

    ec = ESXConfig(ndata, meta, dry_run=False)

    mock_nic = NIC(name="vmnic0", status="Up", link="Up", mac="00:11:22:33:44:55")
    ec._nics = [mock_nic]

    mock_find_by_mac = mocker.patch.object(
        ec.nics, "find_by_mac", return_value=mock_nic
    )

    uplinks = ec.identify_uplinks()

    assert uplinks == [mock_nic]
    mock_find_by_mac.assert_called_once_with(mock_nic.mac)
