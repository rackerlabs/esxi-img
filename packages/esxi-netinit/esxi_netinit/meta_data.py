import json
import logging

from esxi_netinit.metadata import MetaData

logger = logging.getLogger(__name__)


class MetaDataData:
    """Represents meta_data.json."""

    def __init__(self, data: dict) -> None:
        self.metadata = MetaData(
            uuid=data["uuid"],
            hostname=data["hostname"],
            availability_zone=data.get("availability_zone"),
            public_keys=data.get("public_keys", {}),
            admin_pass=data["admin_pass"],
            project_id=data["project_id"],
            random_seed=data["random_seed"],
            launch_index=data["launch_index"],
        )

    @staticmethod
    def from_json_file(path):
        with open(path) as f:
            data = json.load(f)
            return MetaDataData(data)
