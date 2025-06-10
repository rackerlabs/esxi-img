import json
from pathlib import Path

import pytest

THIS_DIR = Path(__file__).parent


def _load_json(file: Path) -> dict:
    with file.open() as f:
        return json.load(f)


@pytest.fixture
def network_data_single():
    return _load_json(THIS_DIR / "data" / "net_data_single.json")


@pytest.fixture
def network_data_multi():
    return _load_json(THIS_DIR / "data" / "net_data_multi.json")
