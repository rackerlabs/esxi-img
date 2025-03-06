# load the driver to access the configdrive
localcli system module load --module iso9660

# get all actual hardware devices
disks=$(find /dev/disks -type f -exec basename {} \;)

for disk in $disks; do
    vsish -e set /vmkModules/iso9660/mount "$disk"
    # "config-2" is the label of the configdrive
    if test -e '/vmfs/volumes/config-2'; then
        echo "$disk" > /tmp/configdrive
        echo "Copying file from configdrive to tmpdir"
        mkdir -p /tmp/config-2
        cd /vmfs/volumes/config-2 || exit 1
        cp -a ./ /tmp/config-2
        break
    else
        vsish -e set '/vmkModules/iso9660/umount' "$disk"
    fi
done
