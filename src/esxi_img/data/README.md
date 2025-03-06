# kickstart data

The `ks-template.cfg` is used as the default kickstart
template if the user does not supply one.

The `pre`, `post`, and `firstboot` are always included
and *MUST* be numerically supported in the order you
expect them to be combined to the final kickstart
script. They must be suffixed with `.py` or `.sh` so
that the correct interpreter is set.
