import tarfile
from pathlib import Path

from esxi_img.tarball import Tarball


def test_complete_paths():
    """Test the iterator functionality with a simple file list."""
    t = Tarball()
    file_list = [
        Path("opt/esxiimg/netinit"),
        Path("opt/esxiimg/esxi_netinit/link.py"),
        Path("opt/esxiimg/esxi_netinit/main.py"),
        Path("opt/esxiimg/esxi_netinit/__init__.py"),
    ]
    for item in file_list:
        t.add_text(item, "")

    expected_paths = [
        (Path("opt/"), tarfile.DIRTYPE, None),
        (Path("opt/esxiimg/"), tarfile.DIRTYPE, None),
        (Path("opt/esxiimg/esxi_netinit/"), tarfile.DIRTYPE, None),
        (Path("opt/esxiimg/esxi_netinit/__init__.py"), tarfile.REGTYPE, ""),
        (Path("opt/esxiimg/esxi_netinit/link.py"), tarfile.REGTYPE, ""),
        (Path("opt/esxiimg/esxi_netinit/main.py"), tarfile.REGTYPE, ""),
        (Path("opt/esxiimg/netinit"), tarfile.REGTYPE, ""),
    ]

    # Convert iterator to list for comparison
    result = list(t.iter_files())

    assert result == expected_paths
