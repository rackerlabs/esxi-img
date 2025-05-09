import pytest


@pytest.fixture
def network_data_single():
    return {
        "links": [
            {
                "ethernet_mac_address": "00:11:22:33:44:55",
                "id": "eth0",
                "mtu": 1500,
                "type": "vif",
                "vif_id": "vif-12345",
            }
        ],
        "networks": [
            {
                "id": "net0",
                "ip_address": "192.168.1.10",
                "netmask": "255.255.255.0",
                "network_id": "public",
                "link": "eth0",
                "type": "ipv4",
                "routes": [
                    {
                        "gateway": "192.168.1.1",
                        "netmask": "255.255.255.0",
                        "network": "192.168.2.0",
                    },
                    {
                        "gateway": "192.168.1.1",
                        "netmask": "0.0.0.0",
                        "network": "0.0.0.0",
                    },
                ],
            }
        ],
        "services": [{"address": "8.8.4.4", "type": "dns"}],
    }


@pytest.fixture
def network_data_multi():
    return {
        "links": [
            {
                "id": "tap47bb4c37-f6",
                "vif_id": "47bb4c37-f60d-474f-8ce5-c7c1d9982585",
                "type": "phy",
                "mtu": 1450,
                "ethernet_mac_address": "14:23:f3:f5:3a:d0",
            },
            {
                "id": "tap1b9c25a9-39",
                "vif_id": "1b9c25a9-396f-43e7-9f1c-a2dcdfd3989c",
                "type": "vlan",
                "mtu": 1450,
                "ethernet_mac_address": "fa:16:3e:07:86:96",
                "vlan_link": "tap47bb4c37-f6",
                "vlan_id": 111,
                "vlan_mac_address": "fa:16:3e:07:86:96",
            },
            {
                "id": "tape3fbe9a7-93",
                "vif_id": "e3fbe9a7-933d-4e27-8ac5-858054be7772",
                "type": "vlan",
                "mtu": 1450,
                "ethernet_mac_address": "fa:16:3e:31:50:d6",
                "vlan_link": "tap47bb4c37-f6",
                "vlan_id": 222,
                "vlan_mac_address": "fa:16:3e:31:50:d6",
            },
            {
                "id": "tapd097f698-89",
                "vif_id": "d097f698-8926-44e1-afe7-09fb03947f23",
                "type": "vlan",
                "mtu": 1450,
                "ethernet_mac_address": "fa:16:3e:48:91:ef",
                "vlan_link": "tap47bb4c37-f6",
                "vlan_id": 444,
                "vlan_mac_address": "fa:16:3e:48:91:ef",
            },
        ],
        "networks": [
            {
                "id": "network0",
                "type": "ipv4",
                "link": "tap47bb4c37-f6",
                "ip_address": "192.168.100.170",
                "netmask": "255.255.255.0",
                "routes": [
                    {
                        "network": "0.0.0.0",
                        "netmask": "0.0.0.0",
                        "gateway": "192.168.100.1",
                    }
                ],
                "network_id": "783b4239-7220-4a74-8253-415539469860",
                "services": [],
            },
            {
                "id": "network1",
                "type": "ipv4",
                "link": "tap1b9c25a9-39",
                "ip_address": "192.168.200.174",
                "netmask": "255.255.255.0",
                "routes": [],
                "network_id": "9608ea7d-18d9-4298-8951-ac9dbe20db06",
                "services": [],
            },
            {
                "id": "network2",
                "type": "ipv4",
                "link": "tape3fbe9a7-93",
                "ip_address": "192.168.0.24",
                "netmask": "255.255.255.0",
                "routes": [],
                "network_id": "ecff22e4-b364-4575-9d2b-dffc83c8d5b7",
                "services": [],
            },
            {
                "id": "network3",
                "type": "ipv4",
                "link": "tapd097f698-89",
                "ip_address": "192.168.10.133",
                "netmask": "255.255.255.0",
                "routes": [],
                "network_id": "c47d5a38-c646-42e8-b6ca-3eecc977d645",
                "services": [],
            },
        ],
        "services": [],
    }
