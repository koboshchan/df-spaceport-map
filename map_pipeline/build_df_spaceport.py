#!/usr/bin/env python3
"""Build a playable Source 2 blockout from the official CS2 defuse template.

The original Blender scene is a 90M-triangle environment capture. This script
creates a compact, collision-safe slice inspired by its space-center hub:
launch tower, service lanes, control rooms, cargo cover, and two bomb sites.
"""

from __future__ import annotations

import hashlib
import argparse
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path


UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
NAMESPACE = uuid.UUID("d2e0f60e-7d78-4b7f-9c41-6e2aa9119e50")


FLOOR = "materials/de_cache/concrete/ch2_blend_concretefloor_03.vmat"
CONCRETE = "materials/concrete/hr_c/hr_concrete_wall_008.vmat"
CONCRETE_DARK = "materials/concrete/hr_c/hr_concrete_wall_006.vmat"
METAL = "materials/metal/hr_metal/hr_metal_wall_002.vmat"
METAL_FLOOR = "materials/metal/hr_metal/hr_metal_floor_002.vmat"
METAL_DIAMOND = "materials/de_cache/metal/ch2_metal_diamondplate_rust_dust_blend.vmat"
RUST = "materials/de_cache/metal/ch2_metal_corrugated_blend_02a.vmat"
HAZARD = "materials/de_nuke/hr_nuke/hazard_stripe_002_trim.vmat"
BLUE_EMIT = "materials/de_nuke/hr_nuke/light_emit_blue.vmat"
SKYBOX = "materials/tools/toolsskybox.vmat"


@dataclass(frozen=True)
class BoxSpec:
    name: str
    center: tuple[float, float, float]
    size: tuple[float, float, float]
    material: str
    angles: tuple[float, float, float] = (0, 0, 0)
    physics: str = "default"


@dataclass(frozen=True)
class PropSpec:
    name: str
    model: str
    origin: tuple[float, float, float]
    angles: tuple[float, float, float] = (0, 0, 0)
    scales: tuple[float, float, float] = (1, 1, 1)


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


def stable_uuid(label: str) -> str:
    return str(uuid.uuid5(NAMESPACE, label))


def stable_ref(label: str) -> str:
    digest = hashlib.blake2b(label.encode("utf-8"), digest_size=8).digest()
    return f"0x{int.from_bytes(digest, 'little'):x}"


def replace_property_line(
    block: list[str], key: str, value: str, *, last: bool
) -> None:
    prefix = f'"{key}"'
    indexes = [index for index, line in enumerate(block) if line.strip().startswith(prefix)]
    if not indexes:
        raise ValueError(f"missing property {key}")
    line_index = indexes[-1] if last else indexes[0]
    line = block[line_index]
    match = re.match(
        rf'^(\s*"{re.escape(key)}"\s+"[^"]+"\s+)".*"\s*$',
        line,
    )
    if not match:
        raise ValueError(f"cannot parse property {key}")
    block[line_index] = f'{match.group(1)}"{value}"'


def replace_last_line(block: list[str], key: str, value: str) -> None:
    replace_property_line(block, key, value, last=True)


def replace_first_line(block: list[str], key: str, value: str) -> None:
    replace_property_line(block, key, value, last=False)


def clone_ids(block: list[str], label: str) -> list[str]:
    text = "\n".join(block)
    id_map = {old: stable_uuid(f"{label}:{old}") for old in UUID_RE.findall(text)}
    for old, new in id_map.items():
        text = text.replace(old, new)
    return text.splitlines()


def make_mesh_clone(template: list[str], spec: BoxSpec, node_id: int) -> list[str]:
    block = clone_ids(template, f"mesh:{spec.name}")
    replace_first_line(block, "nodeID", str(node_id))
    replace_first_line(block, "referenceID", stable_ref(f"ref:{spec.name}"))
    replace_last_line(block, "origin", " ".join(f"{value:g}" for value in spec.center))
    replace_last_line(block, "angles", " ".join(f"{value:g}" for value in spec.angles))
    base_size = (512.0, 512.0, 2.0)
    position_scale = tuple(spec.size[index] / base_size[index] for index in range(3))

    position_stream = next(
        index for index, line in enumerate(block) if '"name" "string" "position:0"' in line
    )
    data_start = next(
        index
        for index in range(position_stream, len(block))
        if '"data" "vector3_array"' in block[index]
    )
    index = data_start + 1
    while index < len(block) and block[index].strip() != "]":
        value = block[index].strip().strip('",')
        parts = value.split()
        if len(parts) == 3:
            point = [float(part) * position_scale[axis] for axis, part in enumerate(parts)]
            indent = block[index][: len(block[index]) - len(block[index].lstrip())]
            suffix = "," if index + 1 < len(block) and block[index + 1].strip() != "]" else ""
            block[index] = f'{indent}"{" ".join(f"{component:.8g}" for component in point)}"{suffix}'
        index += 1
    replace_last_line(block, "scales", "1 1 1")
    replace_last_line(block, "physicsType", spec.physics)

    text = "\n".join(block)
    text = text.replace(
        "materials/dev/dev_measuregeneric01.vmat",
        spec.material,
    )
    return text.splitlines()


def make_entity_clone(template: list[str], spec: PropSpec, node_id: int) -> list[str]:
    block = clone_ids(template, f"prop:{spec.name}")
    replace_first_line(block, "nodeID", str(node_id))
    replace_first_line(block, "referenceID", stable_ref(f"ref:{spec.name}"))
    replace_first_line(block, "model", spec.model)
    replace_last_line(block, "origin", " ".join(f"{value:g}" for value in spec.origin))
    replace_last_line(block, "angles", " ".join(f"{value:g}" for value in spec.angles))
    replace_last_line(block, "scales", " ".join(f"{value:g}" for value in spec.scales))
    block[0] = '\t\t\t"CMapEntity"'
    block[1:] = [("\t\t\t" + line) if line else line for line in block[1:]]
    if not block[-1].rstrip().endswith(","):
        block[-1] = block[-1].rstrip() + ","
    return block


def extract_prop_static_template(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if line.strip() == '"classname" "string" "prop_static"':
            start = index
            while start >= 0 and lines[start].strip() != '"CMapEntity"':
                start -= 1
            if start < 0:
                break
            end = find_block_end(lines, start)
            return lines[start : end + 1]
    raise ValueError("prop_static CMapEntity template not found")


def hide_worldtext(block: list[str]) -> list[str]:
    result = list(block)
    replace_last_line(result, "editorOnly", "1")
    return result


def modify_worldtext_blocks(lines: list[str]) -> list[str]:
    candidates: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        if line.strip() != '"CMapEntity"':
            continue
        end = find_block_end(lines, index)
        body = "\n".join(lines[index : end + 1])
        if '"classname" "string" "point_worldtext"' in body:
            candidates.append((index, end))

    for index, end in reversed(candidates):
        block = hide_worldtext(lines[index : end + 1])
        lines[index : end + 1] = block
    return lines


def relocate_spawns(lines: list[str]) -> None:
    ct_positions = [(-248, -420 + i * 72, 16) for i in range(16)]
    t_positions = [(1272, -420 + i * 72, 16) for i in range(16)]
    counters = {"info_player_counterterrorist": 0, "info_player_terrorist": 0}
    candidates: list[tuple[int, int, str]] = []

    for index, line in enumerate(lines):
        if line.strip() != '"CMapEntity"':
            continue
        end = find_block_end(lines, index)
        body = "\n".join(lines[index : end + 1])
        for classname in counters:
            if f'"classname" "string" "{classname}"' in body:
                candidates.append((index, end, classname))
                break

    for index, end, classname in reversed(candidates):
        position_index = counters[classname]
        position = (ct_positions if classname == "info_player_counterterrorist" else t_positions)[
            position_index
        ]
        counters[classname] += 1
        block = lines[index : end + 1]
        replace_last_line(block, "origin", " ".join(f"{value:g}" for value in position))
        yaw = 90 if classname == "info_player_counterterrorist" else 270
        replace_last_line(block, "angles", f"0 {yaw} 0")
        lines[index : end + 1] = block


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("template")
    parser.add_argument("smartprop")
    parser.add_argument("output")
    parser.add_argument("--no-boxes", action="store_true")
    parser.add_argument("--no-props", action="store_true")
    parser.add_argument("--relocate-spawns", action="store_true")
    args = parser.parse_args()

    template_path = Path(args.template).resolve()
    smartprop_path = Path(args.smartprop).resolve()
    output_path = Path(args.output).resolve()
    lines = template_path.read_text(encoding="utf-8", errors="replace").splitlines()

    mesh_start = next(
        index
        for index, line in enumerate(lines)
        if line.strip() == '"CMapMesh"'
    )
    mesh_end = find_block_end(lines, mesh_start)
    mesh_template = lines[mesh_start : mesh_end + 1]
    if not mesh_template[-1].rstrip().endswith(","):
        mesh_template[-1] = mesh_template[-1].rstrip() + ","

    max_node_id = max(
        int(match.group(1))
        for match in (
            re.search(r'"nodeID" "int" "(\d+)"', line)
            for line in lines
        )
        if match
    )

    floor_tiles = [
        BoxSpec(
            f"ground_{row}_{column}",
            (-112 + column * 416, -344 + row * 336, -16),
            (422, 342, 32),
            FLOOR,
        )
        for row in range(4)
        for column in range(4)
    ]

    boxes = [
        # Main floor, perimeter, and roof.
        *floor_tiles,
        BoxSpec("wall_north", (512, 832, 192), (1664, 32, 384), CONCRETE_DARK),
        BoxSpec("wall_south", (512, -512, 192), (1664, 32, 384), CONCRETE_DARK),
        BoxSpec("wall_west", (-320, 160, 192), (32, 1344, 384), CONCRETE_DARK),
        BoxSpec("wall_east", (1344, 160, 192), (32, 1344, 384), CONCRETE_DARK),
        BoxSpec("sky_roof", (512, 160, 400), (1664, 1344, 16), SKYBOX, physics="none"),
        # Main launch pad and rocket gantry.
        BoxSpec("launch_pad", (512, 320, 8), (352, 352, 16), METAL_FLOOR),
        BoxSpec("pad_hazard_n", (512, 500, 18), (352, 16, 4), HAZARD),
        BoxSpec("pad_hazard_s", (512, 140, 18), (352, 16, 4), HAZARD),
        BoxSpec("gantry_w", (384, 320, 136), (20, 20, 256), METAL, angles=(0, 0, 45)),
        BoxSpec("gantry_e", (640, 320, 136), (20, 20, 256), METAL, angles=(0, 0, -45)),
        BoxSpec("gantry_beam_n", (512, 430, 254), (276, 18, 18), METAL),
        BoxSpec("gantry_beam_s", (512, 210, 254), (276, 18, 18), METAL),
        BoxSpec("gantry_beacon_w", (400, 214, 270), (12, 12, 12), BLUE_EMIT),
        BoxSpec("gantry_beacon_e", (624, 426, 270), (12, 12, 12), BLUE_EMIT),
        # Service lane and central cover.
        BoxSpec("south_lane_wall_n", (512, -264, 64), (448, 20, 128), RUST),
        BoxSpec("south_lane_wall_s", (512, -424, 64), (448, 20, 128), RUST),
        BoxSpec("south_lane_gap_w", (228, -344, 64), (140, 20, 128), RUST),
        BoxSpec("south_lane_gap_e", (796, -344, 64), (140, 20, 128), RUST),
        BoxSpec("mid_cover_a", (304, 56, 40), (96, 160, 80), CONCRETE),
        BoxSpec("mid_cover_b", (640, 56, 40), (96, 160, 80), CONCRETE),
        BoxSpec("mid_cover_c", (430, -64, 32), (64, 64, 64), RUST, angles=(0, 45, 0)),
        BoxSpec("mid_cover_d", (594, -64, 32), (64, 64, 64), RUST, angles=(0, -45, 0)),
        # West and east room shells.
        BoxSpec("west_room_n", (48, -160, 64), (384, 20, 128), CONCRETE),
        BoxSpec("west_room_s", (48, -352, 64), (384, 20, 128), CONCRETE),
        BoxSpec("west_room_w", (-144, -256, 64), (20, 212, 128), CONCRETE),
        BoxSpec("east_room_n", (976, -160, 64), (384, 20, 128), CONCRETE),
        BoxSpec("east_room_s", (976, -352, 64), (384, 20, 128), CONCRETE),
        BoxSpec("east_room_e", (1168, -256, 64), (20, 212, 128), CONCRETE),
        # Bomb-site cover.
        BoxSpec("a_wall_west", (128, 720, 48), (20, 208, 96), CONCRETE),
        BoxSpec("a_wall_east", (384, 720, 48), (20, 208, 96), CONCRETE),
        BoxSpec("a_cover", (256, 584, 40), (128, 48, 80), RUST, angles=(0, 15, 0)),
        BoxSpec("b_wall_west", (640, 720, 48), (20, 208, 96), CONCRETE),
        BoxSpec("b_wall_east", (896, 720, 48), (20, 208, 96), CONCRETE),
        BoxSpec("b_cover", (768, 584, 40), (128, 48, 80), RUST, angles=(0, -15, 0)),
        # Side catwalk stubs and overhead headers.
        BoxSpec("west_catwalk", (72, 300, 176), (288, 72, 12), METAL_DIAMOND),
        BoxSpec("east_catwalk", (952, 300, 176), (288, 72, 12), METAL_DIAMOND),
        BoxSpec("west_catwalk_post_a", (-56, 300, 88), (16, 16, 176), METAL),
        BoxSpec("west_catwalk_post_b", (200, 300, 88), (16, 16, 176), METAL),
        BoxSpec("east_catwalk_post_a", (824, 300, 88), (16, 16, 176), METAL),
        BoxSpec("east_catwalk_post_b", (1080, 300, 88), (16, 16, 176), METAL),
    ]

    props = [
        PropSpec(
            "df_missile",
            "models/generic/missile_01/missile_01.vmdl",
            (512, 326, 36),
            (0, 0, 0),
            (1.2, 1.2, 1.2),
        ),
        PropSpec(
            "df_dish_west",
            "models/generic/antenna_kit_01/antennakit01_dish_01.vmdl",
            (-96, 744, 72),
            (0, 28, 0),
        ),
        PropSpec(
            "df_dish_east",
            "models/generic/antenna_kit_01/antennakit01_dish_01.vmdl",
            (1120, 744, 72),
            (0, -28, 0),
        ),
        PropSpec(
            "df_ibc_west",
            "models/generic/crate_ibc_kit_01/crate_ibc_kit_large_01_a.vmdl",
            (80, 520, 32),
            (0, 20, 0),
        ),
        PropSpec(
            "df_ibc_east",
            "models/generic/crate_ibc_kit_01/crate_ibc_kit_large_01_a.vmdl",
            (944, 520, 32),
            (0, -20, 0),
        ),
        PropSpec(
            "df_barrels",
            "models/generic/metal_barrel_001/metal_barrel_001.vmdl",
            (512, -352, 32),
            (0, 0, 0),
            (1.15, 1.15, 1.15),
        ),
        PropSpec(
            "df_shelves",
            "models/generic/shelve_industrial_kit_01/ch2_shelves_custom_01.vmdl",
            (1040, -360, 0),
            (0, 180, 0),
        ),
        PropSpec(
            "df_pipes",
            "models/props/de_nuke/hr_nuke/metal_pipe_001/metal_pipe_001c_straight_128.vmdl",
            (512, 548, 236),
            (0, 0, 0),
            (1.4, 1.4, 1.4),
        ),
    ]

    prop_template = extract_prop_static_template(smartprop_path)
    inserted: list[str] = []
    next_node_id = max_node_id + 1
    if not args.no_props:
        for spec in props:
            inserted.extend(make_entity_clone(prop_template, spec, next_node_id))
            next_node_id += 1
    if not args.no_boxes:
        for spec in boxes:
            inserted.extend(make_mesh_clone(mesh_template, spec, next_node_id))
            next_node_id += 1

    lines[mesh_start:mesh_start] = inserted
    lines = modify_worldtext_blocks(lines)
    if args.relocate_spawns:
        relocate_spawns(lines)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"WROTE={output_path} BOXES={0 if args.no_boxes else len(boxes)} "
        f"PROPS={0 if args.no_props else len(props)} "
        f"MAX_NODE_ID={next_node_id - 1}"
    )


if __name__ == "__main__":
    main()
