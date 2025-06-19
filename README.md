# ESXi installer image generator

This tool is really a collection of two parts. One part ISO to image generator
and another part with the ability to parse the same metadata that cloud-init
consumes to setup an image.

## Why This Exists

VMware ESXi does not provide OS images that can be used in the cloud like
some other OSes do. You are also unable to install ESXi and then image that
disk and reuse it for a different machine. Due to these limitations, and with
the kind suggestions from Jens Sandmann at SAP Converged Cloud, we've packaged
the installer into an image which can be deployed like a cloud image onto
a system. The installer is then configured to perform a non-interactive
installation and reboot the machine giving the user a working VMware ESXi
machine.

## How It Works

VMware ESXi uses an installer based on RedHat's Anaconda installer, that
they've called weasel. It can be programmatically driven using kickstart
files which have slight differences from RedHat's kickstart files. This
is what is used to perform a non-interactive installation. To facilitate
the data that cloud-init would use to configure an OS image we must
add some extra steps to the process. The installer allows for user
supplied scripts that will run with either busybox ash or Python.
They can run either before or after the installer or the first time
the machine is booted if it was not configured with Secure Boot.

To make the installation work we've split the scripts up into two
parts. The ones that run inside of the installer and the ones that
run on the firstboot.

The installer based pieces involve setting the root password and
getting our firstboot scripts and data copied over to the installed
system so that our firstboot scripts can run.

The firstboot scripts involve configuring the hostname, configuring
the network, enabling the console, enabling SSH and setting the SSH key.

The VMware ESXi installer uses a boot protocol called multiboot
which involves loading multiple modules. Modules that are specifically
crafted tar files are extracted into the installer OS and made available
to it. We utilize this method to get our data and scripts into the
environment.

To create the image we craft a whole disk image with a bootable
partition. We then copy the contents of the ISO into this bootable
partition and configure our tar file to be included as a module
as well as reference a kickstart file which makes the installation
non-interactive.

## Usage

```bash
# using uvx
uvx esxi-img --output esxi.img path/to/esxi.iso

# using pip
python -m venv .venv
source .venv/bin/activate
pip install esxi-img
esxi-img --output esxi.img path/to/esxi.iso
```

## ESXi Network Interfaces

ESXi has physical network interfaces and logical interfaces. The `vmnicX`
interfaces are the physical interfaces and the `vmkX` interfaces are the
logical interfaces, which are also known as VMkernel interfaces.

![Diagram of ESXi interfaces](/docs/assets/esxi-interfaces.png "Explanation of interfaces")
