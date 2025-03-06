for disk in /dev/disk/*; do
    partedUtil fix "$disk" || true
done
