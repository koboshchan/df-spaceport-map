#!/usr/bin/env python3
"""Extract files from a Source 1/2 VPK, including split VPK archives."""

from __future__ import annotations

import argparse
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path


VPK_SIGNATURE = 0x55AA1234
EMBEDDED_ARCHIVE = 0x7FFF


def read_cstring(data: bytes, offset: int) -> tuple[str, int]:
    end = data.index(0, offset)
    return data[offset:end].decode("utf-8", errors="replace"), end + 1


@dataclass(frozen=True)
class Entry:
    path: str
    crc: int
    archive: int
    offset: int
    length: int


def read_entries(path: Path) -> tuple[list[Entry], int]:
    with path.open("rb") as source:
        header = source.read(28)
        if len(header) != 28:
            raise ValueError(f"{path}: truncated VPK header")
        signature, version, tree_size, data_size, *rest = struct.unpack("<7I", header)
        if (signature, version) != (VPK_SIGNATURE, 2):
            raise ValueError(f"{path}: expected a VPK v2 file")
        tree = source.read(tree_size)
        if len(tree) != tree_size:
            raise ValueError(f"{path}: truncated VPK directory tree")

    entries: list[Entry] = []
    cursor = 0
    while cursor < len(tree):
        extension, cursor = read_cstring(tree, cursor)
        if not extension:
            break
        while True:
            directory, cursor = read_cstring(tree, cursor)
            if not directory:
                break
            while True:
                stem, cursor = read_cstring(tree, cursor)
                if not stem:
                    break
                if cursor + 18 > len(tree):
                    raise ValueError(f"{path}: truncated VPK entry metadata")
                crc, preload, archive, offset, length, terminator = struct.unpack_from(
                    "<IHHIIH", tree, cursor
                )
                cursor += 18
                if terminator != 0xFFFF:
                    raise ValueError(f"{path}: malformed VPK directory tree")
                if preload:
                    raise ValueError(f"{path}: preload entries are unsupported")
                relative = f"{stem}.{extension}"
                if directory != " ":
                    relative = f"{directory}/{relative}"
                entries.append(Entry(relative, crc, archive, offset, length))

    # Split VPK directory files use zero here; embedded VPKs store total data size.
    if data_size not in (0, sum(entry.length for entry in entries)):
        raise ValueError(f"{path}: VPK entry sizes do not match header data size")
    _ = rest
    return entries, 28 + tree_size


def read_entry(source_root: Path, main: Path, embedded_offset: int, entry: Entry) -> bytes:
    archive_path = main
    archive_offset = embedded_offset
    if entry.archive != EMBEDDED_ARCHIVE:
        archive_path = main.with_name(f"{main.stem}_{entry.archive:03d}.vpk")
        archive_offset = 0
    with archive_path.open("rb") as source:
        source.seek(archive_offset + entry.offset)
        data = source.read(entry.length)
    if len(data) != entry.length:
        raise ValueError(f"{source_root}: truncated entry {entry.path}")
    if zlib.crc32(data) != entry.crc:
        raise ValueError(f"{source_root}: CRC mismatch for {entry.path}")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vpk", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--prefix",
        action="append",
        default=[],
        help="Only extract paths beginning with this prefix; may be repeated.",
    )
    args = parser.parse_args()

    vpk = args.vpk.resolve()
    output = args.output.resolve()
    entries, embedded_offset = read_entries(vpk)
    prefixes = tuple(prefix.lower() for prefix in args.prefix)
    selected = [
        entry for entry in entries if not prefixes or entry.path.lower().startswith(prefixes)
    ]
    if not selected:
        raise ValueError("No VPK entries matched the requested prefixes")

    for entry in selected:
        destination = (output / entry.path).resolve()
        if output not in destination.parents:
            raise ValueError(f"Unsafe VPK path: {entry.path}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(read_entry(vpk.parent, vpk, embedded_offset, entry))

    print(f"Extracted {len(selected)} of {len(entries)} entries to {output}")


if __name__ == "__main__":
    main()
