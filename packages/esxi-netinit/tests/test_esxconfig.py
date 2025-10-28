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
    host_mock.configure_static_route.assert_called_once_with("192.168.1.1", "default")


def test_configure_management_interface(
    network_data_single, meta_data, host_mock, mocker
):
    ndata = NetworkData(network_data_single)
    meta_data = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta_data, dry_run=False)
    ec.host = host_mock
    nic = NIC(name="vmnic0", status="Up", link="Up", mac="14:23:f3:f5:3a:d0")
    mocker.patch.object(ec, "identify_uplinks", return_value=[nic])
    mgmt_pg = "Management Network"
    mgmt_net = ndata.networks[0]
    ec.configure_interface(ec.management_network, "vSwitch11", mgmt_pg)
    host_mock.create_vswitch.assert_called_once_with("vSwitch11")
    host_mock.portgroup_add.assert_called_once_with("Management Network", "vSwitch11")
    host_mock.add_ip_interface.assert_called_once_with(
        mgmt_net.id, mgmt_pg, mgmt_net.link.ethernet_mac_address, mgmt_net.link.mtu
    )
    host_mock.set_static_ipv4.assert_called_once_with(
        mgmt_net.id, mgmt_net.ip_address, mgmt_net.netmask
    )


def test_no_other_interfaces(network_data_single, meta_data):
    ndata = NetworkData(network_data_single)
    meta_data = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta_data, dry_run=False)
    assert ec.other_networks == []


def test_configure_mgmt_iface_multi_vlan(
    network_data_multi_vlan, meta_data, host_mock, mocker
):
    ndata = NetworkData(network_data_multi_vlan)
    meta_data = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta_data, dry_run=False)
    ec.host = host_mock
    nic = NIC(name="vmnic0", status="Up", link="Up", mac="14:23:f3:f5:3a:d0")
    mocker.patch.object(ec, "identify_uplinks", return_value=[nic])
    mgmt_pg = "Management Network"
    mgmt_net = ndata.networks[0]
    ec.configure_interface(ec.management_network, "vSwitch11", mgmt_pg)
    host_mock.create_vswitch.assert_called_once_with("vSwitch11")
    host_mock.portgroup_add.assert_called_once_with("Management Network", "vSwitch11")
    host_mock.add_ip_interface.assert_called_once_with(
        mgmt_net.id, mgmt_pg, mgmt_net.link.ethernet_mac_address, mgmt_net.link.mtu
    )
    host_mock.set_static_ipv4.assert_called_once_with(
        mgmt_net.id, mgmt_net.ip_address, mgmt_net.netmask
    )


def test_other_vlan_interfaces(network_data_multi_vlan, meta_data, host_mock, mocker):
    ndata = NetworkData(network_data_multi_vlan)
    meta_data = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta_data, dry_run=False)
    ec.host = host_mock
    mock_nics = [
        NIC(name="vmnic0", status="Up", link="Up", mac="14:23:f3:f5:3a:d0"),
        NIC(name="vmnic1", status="Up", link="Up", mac="d4:04:e6:4f:a4:d6"),
    ]

    def identify_uplinks(net):
        if net.link.id == "tape3fbe9a7-93":
            return [mock_nics[1]]
        else:
            return [mock_nics[0]]

    mocker.patch.object(ec, "identify_uplinks", side_effect=identify_uplinks)
    for network in ec.other_networks:
        ec.configure_interface(network)
    host_mock.create_vswitch.assert_has_calls(
        [mocker.call("vSwitch31"), mocker.call("vSwitch32")]
    )
    assert host_mock.create_vswitch.call_count == 2
    host_mock.uplink_add.assert_has_calls(
        [
            mocker.call(nic="vmnic0", switch_name="vSwitch31"),
            mocker.call(nic="vmnic1", switch_name="vSwitch32"),
        ]
    )
    assert host_mock.uplink_add.call_count == 2
    host_mock.portgroup_add.assert_has_calls(
        [
            mocker.call("internal_net_vid_111", "vSwitch31"),
            mocker.call("internal_net_vid_222", "vSwitch32"),
            mocker.call("internal_net_vid_444", "vSwitch31"),
        ]
    )
    assert host_mock.portgroup_add.call_count == 3
    host_mock.portgroup_set_vlan.assert_has_calls(
        [
            mocker.call("internal_net_vid_111", 111),
            mocker.call("internal_net_vid_222", 222),
            mocker.call("internal_net_vid_444", 444),
        ]
    )
    assert host_mock.portgroup_set_vlan.call_count == 3
    host_mock.add_ip_interface.assert_has_calls(
        [
            mocker.call("vmk1", "internal_net_vid_111", "auto", 1450),
            mocker.call("vmk2", "internal_net_vid_222", "auto", 1450),
            mocker.call("vmk3", "internal_net_vid_444", "auto", 1450),
        ]
    )
    assert host_mock.add_ip_interface.call_count == 3


def test_configure_mgmt_iface_multi_phy(
    network_data_multi_phy, meta_data, host_mock, mocker
):
    ndata = NetworkData(network_data_multi_phy)
    meta_data = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta_data, dry_run=False)
    ec.host = host_mock
    mgmt_pg = "Management Network"
    mgmt_net = ndata.networks[0]
    nic = NIC(name="vmnic0", status="Up", link="Up", mac="d4:04:e6:4f:a4:d6")
    mocker.patch.object(ec, "identify_uplinks", return_value=[nic])
    ec.configure_interface(ec.management_network, "vSwitch11", mgmt_pg)
    host_mock.create_vswitch.assert_called_once_with("vSwitch11")
    host_mock.portgroup_add.assert_called_once_with("Management Network", "vSwitch11")
    host_mock.add_ip_interface.assert_called_once_with(
        mgmt_net.id, mgmt_pg, mgmt_net.link.ethernet_mac_address, mgmt_net.link.mtu
    )
    host_mock.set_static_ipv4.assert_called_once_with(
        mgmt_net.id, mgmt_net.ip_address, mgmt_net.netmask
    )


def test_other_phy_interfaces(network_data_multi_phy, meta_data, host_mock, mocker):
    ndata = NetworkData(network_data_multi_phy)
    meta_data = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta_data, dry_run=False)
    ec.host = host_mock
    mock_nics = {
        "tap-stor-100": NIC(
            name="vmnic3", status="Up", link="Up", mac="d4:04:e6:4f:a4:d7"
        ),
        "tap-stor-101": NIC(
            name="vmnic5", status="Up", link="Up", mac="14:23:f3:f6:d8:21"
        ),
    }
    mocker.patch.object(
        ec, "identify_uplinks", side_effect=lambda net: [mock_nics[net.link.id]]
    )
    for network in ec.other_networks:
        ec.configure_interface(network)
    host_mock.create_vswitch.assert_has_calls(
        [mocker.call("vSwitch31"), mocker.call("vSwitch32")]
    )
    assert host_mock.create_vswitch.call_count == 2
    host_mock.uplink_add.assert_has_calls(
        [
            mocker.call(nic="vmnic3", switch_name="vSwitch31"),
            mocker.call(nic="vmnic5", switch_name="vSwitch32"),
        ]
    )
    assert host_mock.uplink_add.call_count == 2
    host_mock.portgroup_add.assert_has_calls(
        [
            mocker.call("tap-stor-100", "vSwitch31"),
            mocker.call("tap-stor-101", "vSwitch32"),
        ]
    )
    assert host_mock.portgroup_add.call_count == 2
    host_mock.add_ip_interface.assert_has_calls(
        [
            mocker.call("vmk1", "tap-stor-100", "d4:04:e6:4f:a4:d7", 9000),
            mocker.call("vmk2", "tap-stor-101", "14:23:f3:f6:d8:21", 9000),
        ]
    )
    assert host_mock.add_ip_interface.call_count == 2


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

    ec.configure_vswitch("vSwitch42", mtu=9000, uplinks=uplinks)

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


def test_identify_uplinks(network_data_multi_vlan, meta_data, mocker):
    ndata = NetworkData(network_data_multi_vlan)
    meta = MetaDataData(meta_data)

    mocker.patch("esxi_netinit.nic_list.NICList.__init__", return_value=None)

    ec = ESXConfig(ndata, meta, dry_run=False)

    mock_nics = [
        NIC(name="vmnic0", status="Up", link="Up", mac="14:23:f3:f5:3a:d0"),
        NIC(name="vmnic1", status="Up", link="Up", mac="d4:04:e6:4f:a4:d6"),
    ]
    nics = {nic.mac: nic for nic in mock_nics}

    mock_find_by_mac = mocker.patch.object(
        ec.nics, "find_by_mac", side_effect=lambda x: nics.get(x)
    )

    for network in ndata.networks:
        uplinks = ec.identify_uplinks(network)
        if network.link.id == "tape3fbe9a7-93":
            mock_nic = mock_nics[1]
        else:
            mock_nic = mock_nics[0]
        assert uplinks == [mock_nic]
        mock_find_by_mac.assert_called_once_with(mock_nic.mac)
        mock_find_by_mac.reset_mock()


def test_static_routes(network_data_multi_phy, meta_data, host_mock, mocker):
    ndata = NetworkData(network_data_multi_phy)
    meta_data = MetaDataData(meta_data)
    ec = ESXConfig(ndata, meta_data, dry_run=False)
    ec.host = host_mock
    ec.configure_static_routes()
    host_mock.configure_static_route.assert_has_calls(
        [
            mocker.call("100.126.64.5", "100.127.0.0/17"),
            mocker.call("100.126.192.5", "100.127.128.0/17"),
        ]
    )
    assert host_mock.configure_static_route.call_count == 2
