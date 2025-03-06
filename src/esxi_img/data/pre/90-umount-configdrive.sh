# unmount the configdrive
vsish -e set '/vmkModules/iso9660/umount' "$(cat /tmp/configdrive)"
