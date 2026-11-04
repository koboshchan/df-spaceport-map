"""Pack the Spaceport map and its compiled addon dependencies into one VPK."""

import argparse
import hashlib
import re
import struct
import zlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from inspect_vpk import read_cstring


MAP = "df_spaceport_player_scale_raytrace"
SIGNATURE = 0x55AA1234
EMBEDDED = 0x7FFF
BLOCK_SIZE = 1 << 20
UNSIGNED = struct.pack("<5I", SIGNATURE, 1, 0, 0, 0)
OPTIONAL_MAP_RESOURCES = {
    f"maps/{MAP}/world_visibility.vvis_c",
    f"maps/{MAP}/cubemaps/env_cubemap_array.vtex_c",
}


@dataclass(frozen=True)
class Entry:
    file: Path
    offset: int
    length: int
    crc: int

    def read(self):
        with self.file.open("rb") as source:
            source.seek(self.offset)
            data = source.read(self.length)
        if len(data) != self.length:
            raise ValueError(f"Truncated resource in {self.file}")
        return data


def map_entries(path):
    with path.open("rb") as source:
        signature, version, size, *_ = struct.unpack("<7I", source.read(28))
        if (signature, version) != (SIGNATURE, 2):
            raise ValueError(f"Expected a VPK v2: {path}")
        tree = source.read(size)
    offset = 0
    while True:
        extension, offset = read_cstring(tree, offset)
        if not extension:
            break
        while True:
            directory, offset = read_cstring(tree, offset)
            if not directory:
                break
            while True:
                name, offset = read_cstring(tree, offset)
                if not name:
                    break
                crc, preload, archive, start, length, terminator = struct.unpack_from("<IHHIIH", tree, offset)
                offset += 18
                if preload or archive != EMBEDDED or terminator != 0xFFFF:
                    raise ValueError(f"Unsupported map entry {directory}/{name}.{extension}")
                filename = f"{name}.{extension}"
                relative = filename if directory == " " else f"{directory}/{filename}"
                yield relative, Entry(path, 28 + size + start, length, crc)


def resource_refs(data):
    if len(data) < 16:
        return
    _, header_version, _, table, count = struct.unpack_from("<IHHII", data)
    if header_version != 12:
        return
    for index in range(count):
        entry = 8 + table + index * 12
        kind, relative, length = struct.unpack_from("<4sII", data, entry)
        if kind != b"RERL" or not length:
            continue
        start = entry + 4 + relative
        offset, refs = struct.unpack_from("<II", data, start)
        for index in range(refs):
            row = start + offset + index * 16 + 8
            name_offset = row + struct.unpack_from("<q", data, row)[0]
            name, _ = read_cstring(data, name_offset)
            yield name.lower().removesuffix("_c") + "_c"


def collect(dist):
    addon = dist / "addon"
    entries = dict(map_entries(addon / "maps" / f"{MAP}.vpk"))
    assets = {
        path.relative_to(addon).as_posix().lower(): path
        for folder in ("models", "materials")
        for path in (addon / folder).rglob("*_c")
    }
    # Source 2 entity lumps can store models as ordinary entity properties.
    vmap = (dist / "source" / f"{MAP}.vmap").read_text(encoding="utf-8-sig")
    models = set(re.findall(r'"model" "string" "(models/df_[^"]+\.vmdl)"', vmap))
    pending = {name for name in entries if name.endswith("_c")} | {model.lower() + "_c" for model in models}
    visited = set()
    stock = set()
    while pending:
        name = pending.pop()
        visited.add(name)
        if name in entries:
            data = entries[name].read()
        else:
            path = assets.get(name)
            if path is None:
                if name in OPTIONAL_MAP_RESOURCES:
                    continue
                if name.startswith(("materials/df_", "models/df_", f"maps/{MAP}/")):
                    raise ValueError(f"Missing custom dependency: {name}")
                stock.add(name)
                continue
            data = path.read_bytes()
            entries[name] = Entry(path, 0, len(data), zlib.crc32(data))
        pending.update(ref for ref in resource_refs(data) if ref not in visited)
    return entries, stock


def make_tree(entries):
    groups = defaultdict(lambda: defaultdict(list))
    for name in entries:
        path = PurePosixPath(name)
        groups[path.suffix[1:]][str(path.parent) if path.parent.parts else " "].append((path.stem, name))

    tree, ordered = bytearray(), []
    start = 0
    for extension, directories in sorted(groups.items()):
        tree.extend(extension.encode() + b"\0")
        for directory, filenames in sorted(directories.items()):
            tree.extend(directory.encode() + b"\0")
            for stem, name in sorted(filenames):
                entry = entries[name]
                tree.extend(stem.encode() + b"\0")
                tree.extend(struct.pack("<IHHIIH", entry.crc, 0, EMBEDDED, start, entry.length, 0xFFFF))
                ordered.append(entry)
                start += entry.length
            tree.append(0)
        tree.append(0)
    tree.append(0)
    return bytes(tree), ordered, start


def write_map(path, entries):
    tree, ordered, length = make_tree(entries)
    md5_size = ((length + BLOCK_SIZE - 1) // BLOCK_SIZE) * 28
    header = struct.pack("<7I", SIGNATURE, 2, len(tree), length, md5_size, 48, len(UNSIGNED))
    temporary = path.with_suffix(".tmp")
    with temporary.open("w+b") as output:
        output.write(header)
        output.write(tree)
        for entry in ordered:
            output.write(entry.read())
        output.seek(len(header) + len(tree))
        md5_table = bytearray()
        remaining = length
        position = 0
        checksum = hashlib.md5(header + tree)
        while remaining:
            block = output.read(min(BLOCK_SIZE, remaining))
            checksum.update(block)
            md5_table.extend(struct.pack("<III", 0x10000 | EMBEDDED, position, len(block)))
            md5_table.extend(hashlib.md5(block).digest())
            position += len(block)
            remaining -= len(block)
        checksums = hashlib.md5(tree).digest() + hashlib.md5(md5_table).digest()
        output.write(md5_table)
        output.write(checksums)
        checksum.update(md5_table + checksums)
        output.write(checksum.digest())
        output.write(UNSIGNED)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    entries, stock = collect(args.dist)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_map(args.output, entries)
    print(f"{len(entries)} packaged entries, {len(stock)} base-game references, {args.output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
