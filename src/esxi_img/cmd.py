#!/usr/bin/env python3
"""esxi-img: A utility to repackage VMware ESXi installer ISO as an OpenStack image."""

import argparse
import importlib.resources
import io
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from pathlib import PurePath

import esxi_netinit
import pycdlib

import esxi_img
from esxi_img.tarball import Tarball

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("esxi-img")


def _read_ks_template() -> str:
    return (
        importlib.resources.files(esxi_img)
        .joinpath("data")
        .joinpath("ks-template.cfg")
        .read_text()
    )


def _gen_ks_snippets() -> str:
    """Generate the hardcoded kickstart pieces that we always include.

    Returns:
        str: the hardcoded snippets formatted correctly to be combined
        with the user suppled data
    """
    output = ""

    data_path = importlib.resources.files(esxi_img).joinpath("data")

    for part in ["pre", "post", "firstboot"]:
        # grab all the snippets
        snips = [item.name for item in data_path.joinpath(part).iterdir()]
        # order them by their name
        snips = sorted(snips)

        for item in snips:
            snip_path = data_path.joinpath(part).joinpath(item)

            if snip_path.suffix == ".py":
                interp = "python"
            elif snip_path.suffix == ".sh":
                interp = "busybox"
            else:
                raise Exception(f"Invalid snippet {part}/{item}")

            output += f"%{part} --interpreter={interp}\n"
            with snip_path.open("r") as f:
                output += f.read()
                output += "\n"

    return output


def generate_ks_template(output_path: str) -> int:
    """Generate a kickstart template file.

    Args:
        output_path: Path to write the kickstart template to

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    logger.info("Generating kickstart template at %s", output_path)
    try:
        # Read the template from package resources
        template_content = _read_ks_template()

        # Write the template to the output file
        output_file = Path(output_path)
        full_template = template_content
        full_template += "\n"
        full_template += _gen_ks_snippets()
        output_file.write_text(full_template)

        logger.info("Successfully wrote kickstart template to %s", output_path)
        return 0
    except Exception:
        logger.exception("Failed to generate kickstart template")
        return 1


def generate_installer_helper(ks_template_path: str | None, output_path: str) -> int:
    """Generate an installer helper tarball.

    Args:
        output_path: Path to write the installer helper tarball to

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    logger.info("Generating installer helper tarball at %s", output_path)

    tarball = Tarball()
    top_dir = Path("esxiimg/")

    if ks_template_path:
        kspath = Path(ks_template_path)
        if not kspath.exists():
            logger.error("Your supplied ks-template %s does not exist.", kspath)
            return 1
        with kspath.open("r") as f:
            ks_template = f.read()
    else:
        ks_template = _read_ks_template()

    tarball.add_text((top_dir / "KS.CFG"), ks_template)

    # add in netinit by walking all the resources
    netinit_files = importlib.resources.files(esxi_netinit)
    for entry in netinit_files.iterdir():
        if entry.name in ["__pycache__", ".", ".."]:
            continue
        path = top_dir / entry.relative_to(netinit_files.parent)
        if entry.is_file():
            tarball.add_file(path, entry)
        elif entry.is_dir():
            continue
        else:
            raise Exception("unsupported file type for {path}")

        # add it to the list of files to include

    try:
        # Add files and directories to the tarball

        # ESXi's VisorFSTar wants "old" GNU format
        with tarfile.open(output_path, "w:gz", format=tarfile.GNU_FORMAT) as tar:
            # Add all files from the list
            for path, ftype, content in tarball.iter_files():
                if ftype == tarfile.DIRTYPE:
                    arcname = str(path) + "/"
                else:
                    arcname = str(path)

                tar_info = tarfile.TarInfo(name=arcname)
                tar_info.uid = 0
                tar_info.gid = 0
                tar_info.type = ftype
                if ftype == tarfile.DIRTYPE:
                    tar_info.mode = 0o0755
                    tar.addfile(tar_info)
                elif isinstance(content, PurePath):
                    tar_info.mode = 0o644
                    with content.open("rb") as f:
                        tar_info.size = content.stat().st_size
                        tar.addfile(tar_info, f)
                elif isinstance(content, str):
                    tar_info.mode = 0o644
                    tar_info.size = len(content)
                    with io.BytesIO(content.encode("utf-8")) as f:
                        tar.addfile(tar_info, f)

        logger.info("Successfully created installer helper tarball at %s", output_path)
        return 0
    except Exception:
        logger.exception("Failed to generate installer helper tarball")
        return 1


def update_esxi_config(file_path: Path):
    lines = file_path.read_text().splitlines()

    updated_lines = []
    for line in lines:
        if line.startswith("modules="):
            if not line.strip().endswith("--- /esxiimg.tgz"):
                line = line.strip() + " --- /esxiimg.tgz"
        elif line.startswith("kernelopt="):
            line = re.sub(r"ks=[^ ]+", "ks=file:///esxiimg/KS.CFG", line)
        updated_lines.append(line)

    file_path.write_text("\n".join(updated_lines) + "\n")


def generate_image(
    iso_path: str,
    output_path: str,
    fmt: str,
    ks_template_path: str | None = None,
    esxiimg_path: str | None = None,
) -> int:
    """Generate an OpenStack image from an ESXi ISO.

    Args:
        iso_path: Path to the ESXi installer ISO
        output_path: Path to write the output disk image to
        fmt: Disk image format
        ks_template_path: Optional path to a kickstart template
        esxiimg_path: Optional path to an installer helper tarball

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    logger.info("Generating OpenStack image from %s to %s", iso_path, output_path)

    out_path = Path(output_path).resolve()
    if out_path.exists():
        logger.error("%s already exists, remove it first", out_path)
        return 1

    # Validate ISO path
    iso_file = Path(iso_path)
    if not iso_file.exists():
        logger.error("ISO file not found: %s", iso_path)
        return 1

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            iso_extract_dir = temp_path / "iso_contents"
            iso_extract_dir.mkdir()

            # Extract ISO contents using pycdlib
            logger.info("Extracting ISO contents to %s", iso_extract_dir)
            _extract_iso(iso_path, iso_extract_dir)

            # Copy kickstart template if provided
            if ks_template_path:
                ks_file = Path(ks_template_path)
                if not ks_file.exists():
                    logger.error("Kickstart template not found: %s", ks_template_path)
                    return 1

                logger.info("Using kickstart template from %s", ks_template_path)

            # Extract installer helper tarball if provided
            if esxiimg_path:
                esxiimg_file = Path(esxiimg_path)
                if not esxiimg_file.exists():
                    logger.error("Installer helper tarball not found: %s", esxiimg_path)
                    return 1

                logger.info("Using installer helper from %s", esxiimg_path)
                shutil.copy(esxiimg_path, iso_extract_dir / "ESXIIMG.TGZ")
            else:
                generate_installer_helper(
                    ks_template_path, iso_extract_dir / "ESXIIMG.TGZ"
                )

            update_esxi_config(iso_extract_dir / "BOOT.CFG")
            update_esxi_config(iso_extract_dir / "EFI" / "BOOT" / "BOOT.CFG")

            # Calculate required size (e.g., ISO size + 200MB)
            size_mb = (
                sum(
                    f.stat().st_size
                    for f in iso_extract_dir.glob("**/*")
                    if f.is_file()
                )
                // (1024 * 1024)
                + 200
            )

            # Create raw disk image
            disk_img_path = temp_path / "disk.img"
            logger.info("Creating disk image (%dmb) at %s", size_mb, disk_img_path)
            if _create_disk_img(iso_extract_dir, disk_img_path, size_mb) != 0:
                return 1

            if fmt != "raw":
                _convert_img(disk_img_path, out_path, fmt)
            else:
                disk_img_path.rename(out_path)

            logger.info("Successfully created image at %s", out_path)
            return 0
    except Exception:
        logger.exception("Failed to generate image")
        return 1


def _extract_iso(iso_path: str, output_dir: Path) -> None:
    """Extract ISO contents using pycdlib.

    Args:
        iso_path: Path to the ISO file
        output_dir: Directory to extract contents to

    Raises:
        Exception: If extraction fails
    """
    iso = pycdlib.PyCdlib()
    iso.open(iso_path)

    # Extract all files
    for dirname, _dirlist, filelist in iso.walk(iso_path="/"):
        # Create directories
        current_dir = output_dir / dirname[1:] if dirname != "/" else output_dir
        current_dir.mkdir(exist_ok=True)

        # Extract files
        for file in filelist:
            new_file = file.rsplit(";", 1)[0]
            file_path = current_dir / new_file
            logger.info("Copying %s/%s to %s/%s", dirname, file, current_dir, new_file)
            with open(file_path, "wb") as f:
                iso.get_file_from_iso_fp(f, iso_path=os.path.join(dirname, file))

    iso.close()


def _create_disk_img(source_dir: Path, image_path: str, size_mb: int) -> int:
    system = platform.system().lower()
    if system == "darwin":
        return _create_disk_img_macos(source_dir, image_path, size_mb)
    elif system == "linux":
        return _create_disk_img_linux(source_dir, image_path, size_mb)
    else:
        raise RuntimeError(f"Unsupported OS: {system}")


def _create_disk_img_macos(source_dir: Path, image_path: str, size_mb: int) -> int:
    image_path = Path(image_path).resolve()
    img_dmg_path = image_path.with_suffix("".join(image_path.suffixes) + ".dmg")

    # Create an empty disk image with a FAT32 partition
    subprocess.run(
        [
            "hdiutil",
            "create",
            "-size",
            f"{size_mb}m",
            "-fs",
            "FAT32",
            "-layout",
            "GPTSPUD",
            "-volname",
            "EFI",
            "-o",
            str(image_path),
        ],
        check=True,
    )

    # Attach the disk image and get the device name
    result = subprocess.run(
        ["hdiutil", "attach", str(img_dmg_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    parts = [
        [item.strip() for item in line.split("\t")]
        for line in result.stdout.split("\n")
        if line != ""
    ]
    # the last line and the last field is the mount point
    mount_path = parts[-1][-1]
    # the last line and the first field is the mount device
    mount_dev = parts[-1][0]
    # the first line and the first field is the image device
    device = parts[0][0]

    if not device:
        logger.error("Failed to determine device attachment via hdiutil")
        logger.error(result.stdout)
        return 1
    if not mount_dev:
        logger.error("Failed to determine partition device via hdiutil")
        logger.error(result.stdout)
        logger.error(parts)
        return 1
    if not mount_path:
        logger.error("Failed to determine partition mount via hdiutil")
        logger.error(result.stdout)
        return 1
    logger.info("Mounted temp disk to %s", mount_path)
    try:
        # Step 6: Copy files into the mounted EFI partition
        for file in source_dir.iterdir():
            dest = Path(mount_path) / file.name
            if file.is_file():
                shutil.copy(file, dest)
            elif file.is_dir():
                shutil.copytree(file, dest)

        subprocess.run(["diskutil", "unmount", mount_dev], check=True)

        # use gdisk to fix up the EFI partition to a system partition
        # 1. open the file
        # 2. "t" - change partition type
        # 3. "ef00" - efi system partition
        # 4. "w" - write new partition header
        # 5. "y" - yes make this change
        gdisk_cmds = [
            "t",
            "ef00",
            "w",
            "y",
        ]

        # each command followed by [Enter]
        gdisk_input = "\n".join(gdisk_cmds) + "\n"
        subprocess.run(
            ["gdisk", str(img_dmg_path)], input=gdisk_input, check=True, text=True
        )

    finally:
        # Step 8: Detach the disk image
        subprocess.run(["hdiutil", "detach", device], check=True)

    img_dmg_path.rename(image_path)
    return 0


def _create_disk_img_linux(source_dir: Path, output_path: Path, size_mb: int) -> int:
    """Create a disk image from the extracted ISO contents.

    Args:
        source_dir: Directory containing the extracted ISO contents
        output_path: Path to write the disk image to

    Raises:
        Exception: If disk image creation fails
    """
    try:
        # Create raw disk image
        subprocess.run(
            ["qemu-img", "create", "-f", "raw", str(output_path), f"{size_mb}M"],
            check=True,
        )

        # Format the raw disk and copy files
        loopdev = None
        mount_dir = None
        try:
            loopdev = (
                subprocess.check_output(["losetup", "--show", "-f", str(output_path)])
                .decode()
                .strip()
            )

            commands = (
                "\n".join(
                    [
                        "g",  # new GPT partition table,
                        "n",  # new partition,
                        "1",  # first partition,
                        "",  # start at default,
                        "",  # fill up whole space,
                        "t",  # change partition type,
                        "uefi",  # to UEFI
                        "w",  # save
                    ]
                )
                + "\n"
            )
            subprocess.run(["fdisk", loopdev], input=commands.encode(), check=False)

            # Detach and reattach loop device to refresh partition table.
            # Poor man's partprobe.
            subprocess.run(["losetup", "-d", loopdev], check=True)
            loopdev = (
                subprocess.check_output(
                    ["losetup", "--show", "-f", "--partscan", str(output_path)]
                )
                .decode()
                .strip()
            )

            partdev = loopdev + "p1"
            subprocess.run(["mkfs.vfat", "-F", "32", partdev], check=True)
            mount_dir = tempfile.mkdtemp()
            subprocess.run(["mount", partdev, mount_dir], check=True)

            for item in os.listdir(source_dir):
                src = os.path.join(source_dir, item)
                dst = os.path.join(mount_dir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy(src, dst)

            subprocess.run(["umount", mount_dir], check=True)
        finally:
            if mount_dir:
                os.rmdir(mount_dir)
            if loopdev:
                subprocess.run(["losetup", "-d", loopdev], check=True)

        return 0
    except subprocess.CalledProcessError as e:
        raise Exception(
            f"Failed to create image: {e.cmd}\nstdout:\n{e.stdout}"
            f"\nstderr:\n{e.stderr}"
        ) from None


def _convert_img(raw_path: Path, out_path: Path, fmt: str):
    try:
        # Convert raw disk to VMDK
        subprocess.run(
            [
                "qemu-img",
                "convert",
                "-f",
                "raw",
                "-O",
                fmt,
                str(raw_path),
                str(out_path),
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise Exception(
            f"Failed to convert image: {e.cmd}\nstdout:\n{e.stdout}"
            f"\nstderr:\n{e.stderr}"
        ) from None


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create the command line argument parser.

    Returns:
        argparse.ArgumentParser: The configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Convert VMware ESXi installer ISO to OpenStack image"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    subparsers.required = True

    # ks-template subcommand
    ks_parser = subparsers.add_parser("ks-template", help="Generate kickstart template")
    ks_parser.add_argument(
        "KICKSTART",
        type=str,
        help="Output kickstart template filename",
    )

    # installer-helper subcommand
    helper_parser = subparsers.add_parser(
        "installer-helper", help="Generate installer helper tarball"
    )
    helper_parser.add_argument(
        "--ks-template", type=str, help="Path to kickstart template file (optional)"
    )
    helper_parser.add_argument(
        "TARBALL",
        type=str,
        help="Output installer helper tarball filename",
    )

    # gen-img subcommand
    img_parser = subparsers.add_parser(
        "gen-img", help="Generate OpenStack image from ESXi ISO"
    )
    img_parser.add_argument(
        "--ks-template", type=str, help="Path to kickstart template file (optional)"
    )
    img_parser.add_argument(
        "--esxiimg", type=str, help="Path to installer helper tarball (optional)"
    )
    img_parser.add_argument(
        "--format",
        type=str,
        choices=["raw", "qcow2", "vmdk"],
        default="raw",
        help="Format of the generated disk image (default: %(default)s)",
    )
    img_parser.add_argument("ISO", type=str, help="Path to ESXi installer ISO")
    img_parser.add_argument(
        "DISKIMG",
        type=str,
        help="Output disk image filename",
    )

    return parser


def main() -> int:
    """Main entry point for the esxi-img utility.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    parser = _create_argument_parser()
    args = parser.parse_args()

    try:
        if args.command == "ks-template":
            return generate_ks_template(args.KICKSTART)
        elif args.command == "installer-helper":
            return generate_installer_helper(args.ks_template, args.TARBALL)
        elif args.command == "gen-img":
            return generate_image(
                args.ISO, args.DISKIMG, args.format, args.ks_template, args.esxiimg
            )
        else:
            logger.error("Unknown command: %s", args.command)
            return 1
    except Exception:
        logger.exception("Failed to execute %s", args.command)
        return 1


if __name__ == "__main__":
    sys.exit(main())
