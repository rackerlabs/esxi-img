import argparse
import logging
import logging.handlers
import os
import sys
from pathlib import Path

from esxi_netinit.esxconfig import ESXConfig
from esxi_netinit.meta_data import MetaDataData
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


def main(config_dir, dry_run):
    config_path = Path(config_dir)
    network_data_file = config_path / "network_data.json"
    meta_data_file = config_path / "meta_data.json"

    if not network_data_file.exists():
        logger.error("Missing network_data.json in %s", config_dir)
        sys.exit(1)

    if not meta_data_file.exists():
        logger.error("Missing meta_data.json in %s", config_dir)
        sys.exit(1)

    network_data = NetworkData.from_json_file(network_data_file)
    meta_data = MetaDataData.from_json_file(meta_data_file)

    esx = ESXConfig(network_data, meta_data, dry_run=dry_run)
    esx.configure_hostname()
    esx.clean_default_network_setup(OLD_MGMT_PG, OLD_VSWITCH)

    # this configures the Management Network to the default vSwitch
    esx.configure_interface(esx.management_network, NEW_VSWITCH, NEW_MGMT_PG)
    esx.configure_default_route()
    esx.configure_requested_dns()

    # this configures the remaining networks, adding more vSwitches as necessary
    for net in esx.other_networks:
        esx.configure_interface(net)

    # Finally add any static routes
    esx.configure_static_routes()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Network configuration script")
    parser.add_argument(
        "config_dir",
        help="Path to the configuration dir containing "
        "network_data.json, meta_data.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making any changes",
    )
    args = parser.parse_args()

    setup_logger()

    try:
        main(args.config_dir, args.dry_run)
    except Exception:
        logger.exception("Error configuring network")
        sys.exit(1)
