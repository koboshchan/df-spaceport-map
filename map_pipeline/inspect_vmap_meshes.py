#!/usr/bin/env python3
"""Summarize CMapMesh and CMapEntity nodes in a text DMX .vmap."""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path


UUID_RE = re.compile(
    r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
    r'[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
)
VECTOR_RE = re.compile(r'"([-+0-9.eE]+) ([-+0-9.eE]+) ([-+0-9.eE]+)"')


def find_block_end(lines: list[str], start: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    started = False
    for index in range(start, len(lines)):
        for char in lines[index]:
            if escaped:
                escaped = False
                continue
            if char == "\\" and in_string:
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
                started = True
            elif char == "}":
                depth -= 1
                if started and depth == 0:
                    return index
    raise ValueError(f"unclosed block at line {start + 1}")


def parse_vector(line: str) -> list[float] | None:
    match = VECTOR_RE.search(line)
    if not match:
        return None
    return [float(match.group(1)), float(match.group(2)), float(match.group(3))]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: inspect_vmap_meshes.py <map.vmap>")

    path = Path(sys.argv[1]).resolve()
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    meshes = []
    entities = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped in {'"CMapMesh"', '"CMapEntity"'}:
            end = find_block_end(lines, index)
            block = lines[index : end + 1]
            body = "\n".join(block)
            ids = UUID_RE.findall(body)
            origins = [
                parse_vector(item)
                for item in block
                if item.strip().startswith('"origin"')
            ]
            origins = [value for value in origins if value is not None]
            scales = [
                parse_vector(item)
                for item in block
                if item.strip().startswith('"scales"')
            ]
            scales = [value for value in scales if value is not None]
            record = {
                "line": index + 1,
                "end_line": end + 1,
                "root_id": ids[0] if ids else None,
                "origins": origins,
                "scales": scales,
            }
            if stripped == '"CMapMesh"':
                materials = []
                for offset, item in enumerate(block):
                    if item.strip() == '"materials" "string_array"':
                        cursor = offset + 1
                        while cursor < len(block) and block[cursor].strip() != "[":
                            cursor += 1
                        cursor += 1
                        while cursor < len(block) and block[cursor].strip() != "]":
                            value = block[cursor].strip().strip('",')
                            if value:
                                materials.append(value)
                            cursor += 1
                        break
                positions = []
                in_position_data = False
                for item in block:
                    if '"name" "string" "position:0"' in item:
                        continue
                    if not in_position_data and '"data" "vector3_array"' in item:
                        in_position_data = True
                        continue
                    if in_position_data:
                        if item.strip() == "]":
                            break
                        value = item.strip().strip('",')
                        if value:
                            parts = value.split()
                            if len(parts) == 3 and all(
                                re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", part)
                                for part in parts
                            ):
                                positions.append([float(part) for part in parts])
                bounds = None
                if positions:
                    bounds = {
                        "min": [min(point[i] for point in positions) for i in range(3)],
                        "max": [max(point[i] for point in positions) for i in range(3)],
                    }
                    bounds["size"] = [
                        bounds["max"][i] - bounds["min"][i] for i in range(3)
                    ]
                record.update(
                    {
                        "vertices": len(positions),
                        "bounds_local": bounds,
                        "materials": materials,
                    }
                )
                meshes.append(record)
            else:
                classname = None
                for item in block:
                    match = re.search(r'"classname" "string" "([^"]+)"', item)
                    if match:
                        classname = match.group(1)
                        break
                record["classname"] = classname
                entities.append(record)

    world = None
    for index, line in enumerate(lines):
        if line.strip() == '"world" "CMapWorld"':
            end = find_block_end(lines, index)
            world = {"line": index + 1, "end_line": end + 1}
            break

    print(json.dumps({"world": world, "meshes": meshes, "entities": entities}, indent=2))


if __name__ == "__main__":
    main()
