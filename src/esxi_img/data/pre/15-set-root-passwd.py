import json

input_file = "/vmfs/volumes/config-2/openstack/latest/meta_data.json"
# this output file has to be referenced in ../main.cfg
output_file = "/tmp/rootpw"

with open(input_file) as f:
    meta_data = json.load(f)

with open(output_file, "w") as f:
    f.write("rootpw {}\n".format(meta_data["admin_pass"]))
