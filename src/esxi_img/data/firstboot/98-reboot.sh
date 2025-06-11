logger -s -t esxi-netinit "Triggering reboot in 20 seconds"
/bin/loadESXEnable -e && /usr/lib/vmware/loadesx/bin/loadESX.py || true
esxcli system shutdown reboot -d 20 -r "rebooting ESXi after host config"
