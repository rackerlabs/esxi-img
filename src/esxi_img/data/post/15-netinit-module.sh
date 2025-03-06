_bootbank=/vmfs/volumes/BOOTBANK1
boot_cfg="$_bootbank/boot.cfg"

# copy over the esxiimg tools. compress again because bootloader
# decompressed it at first stage
cat /tardisks/esxiimg.tgz | gzip -c > "$_bootbank/esxiimg.tgz"

# adjust the kernel command line to include the nice tar.gz
sed -i -e 's|^modules=\(.*\)|modules=\1 --- esxiimg.tgz|g' "$boot_cfg"
