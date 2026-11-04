#!/usr/bin/env python3
"""Remove background mountain cells and legacy boundary walls from the old VMap."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from build_df_spaceport import find_block_end


BACKGROUND_RE = re.compile(
    r"(?:SM_Terrain_DesertFar(?:Mountain|Valley)|"
    r"SM_Nature_Rock_(?:Big|Cliff)|"
    r"SM_Destructible_Rock_Fragments)",
    re.IGNORECASE,
)
BOUNDARY_WALL_ORIGINS = {
    "-1010 -50 300",
    "1510 -50 300",
    "250 -1300 300",
    "250 1200 300",
}


def is_background_cell(cell: dict) -> bool:
    names = cell.get("object_names") or []
    hits = [name for name in names if BACKGROUND_RE.search(name)]
    if not hits:
        return False
    return len(names) <= 4 or len(hits) / len(names) >= 0.6


def string_values(block: list[str], key: str, value_type: str) -> list[str]:
    pattern = re.compile(
        rf'^\s*"{re.escape(key)}"\s+"{re.escape(value_type)}"\s+"([^"]*)"'
    )
    result = []
    for line in block:
        match = pattern.match(line)
        if match:
            result.append(match.group(1))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("manifest")
    parser.add_argument("collision_manifest")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    collision_manifest = json.loads(
        Path(args.collision_manifest).read_text(encoding="utf-8")
    )
    removed_models = {
        cell["vmdl"]
        for cell in manifest["cells"]
        if is_background_cell(cell)
    }
    removed_models.update(
        cell["vmdl"]
        for cell in collision_manifest["cells"]
        if is_background_cell(cell)
    )

    source = Path(args.input).resolve()
    output = Path(args.output).resolve()
    lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
    kept: list[str] = []
    removed_entities = 0
    removed_meshes = 0
    index = 0
    while index < len(lines):
        block_type = lines[index].strip()
        if block_type not in {'"CMapEntity"', '"CMapMesh"'}:
            kept.append(lines[index])
            index += 1
            continue

        end = find_block_end(lines, index)
        block = lines[index : end + 1]
        remove = False
        if block_type == '"CMapEntity"':
            models = string_values(block, "model", "string")
            remove = bool(models and models[0] in removed_models)
            if remove:
                removed_entities += 1
        else:
            origins = string_values(block, "origin", "vector3")
            remove = bool(origins and origins[-1] in BOUNDARY_WALL_ORIGINS)
            if remove:
                removed_meshes += 1

        if not remove:
            kept.extend(block)
        index = end + 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(kept) + "\n", encoding="utf-8")
    print(
        f"WROTE={output} REMOVED_ENTITIES={removed_entities} "
        f"REMOVED_MESHES={removed_meshes} REMOVED_MODELS={len(removed_models)}"
    )


if __name__ == "__main__":
    main()
