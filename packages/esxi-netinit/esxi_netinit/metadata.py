from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import Optional


@dataclass
class MetaData:
    uuid: str
    admin_pass: str
    hostname: str
    project_id: str
    random_seed: str
    launch_index: Optional[int] = 0
    availability_zone: Optional[str] = None
    meta: Dict[str, str] = field(default_factory=dict)
    public_keys: Dict[str, str] = field(default_factory=dict)
    devices: "list | None" = field(default=None)
    dedicated_cpus: "list | None" = field(default=None)
