#!/usr/bin/env python3
"""List paths and sizes from a Source 1/2 VPK directory tree."""

from __future__ import annotations

import struct
import sys
from pathlib import Path


def read_cstring(data: bytes, offset: int) -> tuple[str, int]:
    end = data.index(0, offset)
    return data[offset:end].decode("utf-8", errors="replace"), end + 1


def inspect(path: Path) -> None:
    data = path.read_bytes()
    signature, version, tree_size = struct.unpack_from("<III", data, 0)
    if signature != 0x55AA1234:
        raise ValueError(f"{path}: not a VPK file")

    header_size = 12
    if version == 2:
        header_size += 16
    elif version != 1:
        raise ValueError(f"{path}: unsupported VPK version {version}")

    tree_end = header_size + tree_size
    offset = header_size
    entries = []
    while offset < tree_end:
        extension, offset = read_cstring(data, offset)
        if not extension:
            break
        while True:
            directory, offset = read_cstring(data, offset)
            if not directory:
                break
            while True:
                stem, offset = read_cstring(data, offset)
                if not stem:
                    break
                crc, preload, archive, entry_offset, length, terminator = (
                    struct.unpack_from("<IHHIIH", data, offset)
                )
                offset += 18
                if terminator != 0xFFFF:
                    raise ValueError(f"{path}: malformed directory tree")
                entries.append(
                    (
                        f"{directory}/{stem}.{extension}".lstrip("/"),
                        length,
                        preload,
                        archive,
                        entry_offset,
                        crc,
                    )
                )

    print(
        f"PATH={path} VERSION={version} HEADER={header_size} "
        f"TREE={tree_size} ENTRIES={len(entries)}"
    )
    for entry in entries:
        print(
            f"{entry[0]} length={entry[1]} preload={entry[2]} "
            f"archive={entry[3]} offset={entry[4]} crc={entry[5]:08x}"
        )


if __name__ == "__main__":
    for argument in sys.argv[1:]:
        inspect(Path(argument))
