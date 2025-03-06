_bootbank=/vmfs/volumes/BOOTBANK1
boot_cfg="$_bootbank/boot.cfg"

# put everything in a nice tar.gz in the bootbank1
tar c -z -f "$_bootbank/config-2.tgz" -C /tmp config-2

# adjust the kernel command line to include the nice tar.gz
sed -i -e 's|^modules=\(.*\)|modules=\1 --- config-2.tgz|g' "$boot_cfg"
