import argparse
import logging
import logging.handlers
import os
import sys

from esxi_netinit.esxconfig import ESXConfig
from esxi_netinit.network_data import NetworkData

OLD_MGMT_PG = "Management Network"
OLD_VSWITCH = "vSwitch0"
NEW_MGMT_PG = "mgmt"
NEW_VSWITCH = "vSwitch22"


logger = logging.getLogger(__name__)


def setup_logger(log_level=logging.INFO):
    """Set up the root logger.

    Output to stdout and to syslog at the requested log_level.
    """
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level,
    )

    app_name = os.path.basename(sys.argv[0])

    syslog_fmt = logging.Formatter(f"{app_name}: %(levelname)s - %(message)s")
    try:
        syslog_handler = logging.handlers.SysLogHandler()
        syslog_handler.setLevel(log_level)
        syslog_handler.setFormatter(syslog_fmt)
        logging.getLogger().addHandler(syslog_handler)
    except Exception:
        logger.error("Failed to setup syslog for logging")


def main(json_file, dry_run):
    network_data = NetworkData.from_json_file(json_file)
    esx = ESXConfig(network_data, dry_run=dry_run)
    esx.clean_default_network_setup(OLD_MGMT_PG, OLD_VSWITCH)
    esx.configure_vswitch(
        uplink=esx.identify_uplink(), switch_name=NEW_VSWITCH, mtu=9000
    )

    esx.configure_vlans()
    esx.add_default_mgmt_interface(NEW_MGMT_PG, NEW_VSWITCH)
    esx.configure_management_interface()
    esx.configure_default_route()
    esx.configure_requested_dns()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Network configuration script")
    parser.add_argument("json_file", help="Path to the JSON configuration file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making any changes",
    )
    args = parser.parse_args()

    setup_logger()

    try:
        main(args.json_file, args.dry_run)
    except Exception:
        logger.exception("Error configuring network")
        sys.exit(1)
