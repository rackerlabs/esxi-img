# ESX Networking setup scripts

`esxi_netinit` is a Python program to configure network information on an ESXi
host, and is intended to be run during the `firstboot` of ESXi after install.

It will read data provided in the Openstack config-drive
[format](https://docs.openstack.org/nova/latest/user/metadata.html#config-drives)
and use that to configure the host.

## config-drive files

The files from the config-drive that are used are:
 - `meta_data.json` (to get the supplied hostname)
 - `network_data.json` (to get the network configuration & DNS servers)
 - `user_data` (optional, to control what settings are applied)

## What it does

1. Set the device hostname (from the value supplied in `meta_data.json`)
2. Delete the default ESXi vmkernel (`vmk0`), portgroup `Management Network` and
  vswitch (`vswitch0`)
3. Create a new vSwitch, portgroup and vmkernel for the management network (from
  the data supplied in `network_data.json`)
4. Configure the default route (from the data supplied in `network_data.json`)
5. Configure the DNS server(s) (from the data supplied in `network_data.json`)
6. (optionally) Configure additional vswitches, portroups & vmkernels
  (from the data supplied in `network_data.json`)
7. Configure any static routes (from the data supplied in `network_data.json`)

The device should be rebooted after this configuration is applied

## user_data settings

The `user_data` file can be used to control some of the actions of the script.

It is a `yaml` file, and esxi_netinit will read the following keys (default values shown):
```yaml
configure_all_networks: false
management_vswitch: "vSwitch0"
management_portgroup: "Management Portgroup"
first_extra_vswitch_number: 1
```

The keys have the following meanings:

| Key | Default | Meaning |
|:---|:---|:---|
| `configure_all_networks` | `false` | Whether to only configure the management network (default), or all defined networks |
| `management_vswitch` | "vSwitch0" | Name of the vSwitch to create for the management network |
| `management_portgroup` | "Management Portrgoup" | Name of the portgroup for the vSwitch on the management network |
| `first_extra_vswitch_number` | 1 | vSwitches for additional networks will be numbered in sequence starting from this value |

Note that vmkernel nics will be created strictly in sequence `vmk0`, `vmk1`, etc.

The default behaviour of the code is to create a single vSwitch, portgroup and vmkernel with the same
names that the ESXi installer gives them - this is because other VMware tooling may expect
new hypervisor hosts to be configured in this way (e.g. for enrolling into VCF).

However, if your use-case allows for additional network configuration to be applied to
the host during provisioning, setting `configure_all_networks: true` will allow
esxi_netinit to do that for you.
