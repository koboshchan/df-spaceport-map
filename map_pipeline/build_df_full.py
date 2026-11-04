#!/usr/bin/env python3
"""Build the full-scene Source 2 map from exported Blender cell manifests."""

from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from build_df_spaceport import (  # noqa: E402
    BLUE_EMIT,
    CONCRETE,
    CONCRETE_DARK,
    FLOOR,
    METAL,
    SKYBOX,
    BoxSpec,
    PropSpec,
    clone_ids,
    extract_prop_static_template,
    find_block_end,
    make_entity_clone,
    make_mesh_clone,
    modify_worldtext_blocks,
    replace_first_line,
    replace_last_line,
    stable_ref,
)

SOURCE_MODEL_SCALE = 30.0
SOURCE_LAYOUT_SCALE = 1.0
WORLD_XY_EXTENT = 14336.0
WORLD_Z_EXTENT = 8192.0
BACKGROUND_GEOMETRY_RE = __import__("re").compile(
    r"(?:SM_Terrain_DesertFar(?:Mountain|Valley)|"
    r"SM_Nature_Rock_(?:Big|Cliff)|"
    r"SM_Destructible_Rock_Fragments)",
    __import__("re").IGNORECASE,
)


def should_skip_background_geometry(cell: dict) -> bool:
    object_names = cell.get("object_names") or []
    hits = [name for name in object_names if BACKGROUND_GEOMETRY_RE.search(name)]
    if not hits:
        return False
    return len(object_names) <= 4 or len(hits) / len(object_names) >= 0.6


def clamp_point_to_world(
    point: tuple[float, float, float],
    target_center: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        max(
            target_center[0] - WORLD_XY_EXTENT,
            min(target_center[0] + WORLD_XY_EXTENT, point[0]),
        ),
        max(
            target_center[1] - WORLD_XY_EXTENT,
            min(target_center[1] + WORLD_XY_EXTENT, point[1]),
        ),
        max(
            target_center[2] - WORLD_Z_EXTENT,
            min(target_center[2] + WORLD_Z_EXTENT, point[2]),
        ),
    )


def transform_source_point(
    point: tuple[float, float, float],
    source_center: tuple[float, float, float],
    target_center: tuple[float, float, float],
    cell_size: float,
    layout_scale: float,
    model_scale: float,
) -> tuple[float, float, float]:
    anchor = (
        math.floor(float(point[0]) / cell_size) * cell_size,
        math.floor(float(point[1]) / cell_size) * cell_size,
        0.0,
    )
    anchor_world = (
        target_center[0] + (anchor[0] - source_center[0]) * layout_scale,
        target_center[1] + (anchor[1] - source_center[1]) * layout_scale,
        target_center[2] + (anchor[2] - source_center[2]) * model_scale,
    )
    local = tuple(float(point[axis]) - anchor[axis] for axis in range(3))
    transformed = tuple(
        anchor_world[axis] + local[axis] * model_scale
        for axis in range(3)
    )
    return clamp_point_to_world(transformed, target_center)


def transform_cell_origin(
    cell: dict,
    source_center: tuple[float, float, float],
    target_center: tuple[float, float, float],
    cell_size: float,
    layout_scale: float,
    model_scale: float,
) -> tuple[float, float, float]:
    source_origin = tuple(
        float(value)
        for value in cell.get(
            "cell_origin_blender",
            (
                cell["grid"][0] * cell_size,
                cell["grid"][1] * cell_size,
                0.0,
            ),
        )
    )
    return transform_source_point(
        source_origin,
        source_center,
        target_center,
        cell_size,
        layout_scale,
        model_scale,
    )


def relocate_spawns(lines: list[str]) -> None:
    spawn_y = (-1100, -940, -780, -620)
    ct_positions = [
        (x, y, 16)
        for x in (-128, 32, 192, 352)
        for y in spawn_y
    ]
    t_positions = [
        (x, y, 16)
        for x in (672, 832, 992, 1152)
        for y in spawn_y
    ]
    counters = {"info_player_counterterrorist": 0, "info_player_terrorist": 0}
    candidates = []

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
        position = (
            ct_positions if classname == "info_player_counterterrorist" else t_positions
        )[position_index]
        counters[classname] += 1
        block = lines[index : end + 1]
        replace_last_line(block, "origin", " ".join(f"{value:g}" for value in position))
        yaw = 90 if classname == "info_player_counterterrorist" else 270
        replace_last_line(block, "angles", f"0 {yaw} 0")
        lines[index : end + 1] = block


def make_floor_tiles() -> list[BoxSpec]:
    return [
        BoxSpec("center_spawn_platform", (512, -900, -16), (1800, 900, 32), FLOOR),
    ]


def make_human_scale_mannequin() -> list[BoxSpec]:
    return [
        BoxSpec("human_scale_torso", (640, -800, 52), (28, 18, 34), METAL),
        BoxSpec("human_scale_head", (640, -800, 82), (14, 14, 14), METAL),
        BoxSpec("human_scale_leg_left", (631, -800, 17), (10, 14, 34), METAL),
        BoxSpec("human_scale_leg_right", (649, -800, 17), (10, 14, 34), METAL),
        BoxSpec("human_scale_arm_left", (619, -800, 52), (8, 14, 34), METAL),
        BoxSpec("human_scale_arm_right", (661, -800, 52), (8, 14, 34), METAL),
    ]


def extract_class_template(path: Path, classname: str) -> list[str]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if line.strip() != '"CMapEntity"':
            continue
        end = find_block_end(lines, index)
        body = "\n".join(lines[index : end + 1])
        if f'"classname" "string" "{classname}"' in body:
            return lines[index : end + 1]
    raise ValueError(f"{classname} CMapEntity template not found")


def set_string_property(block: list[str], key: str, value: str) -> None:
    prefix = f'"{key}"'
    indexes = [
        index for index, line in enumerate(block) if line.strip().startswith(prefix)
    ]
    if indexes:
        replace_last_line(block, key, value)
        return

    classname_index = next(
        index
        for index, line in enumerate(block)
        if '"classname" "string"' in line
    )
    indent = block[classname_index][
        : len(block[classname_index]) - len(block[classname_index].lstrip())
    ]
    block.insert(classname_index + 1, f'{indent}"{key}" "string" "{value}"')


def light_brightness(light: dict, model_scale: float) -> float:
    energy = max(0.0, float(light["energy"]))
    # Scaling the world moves surfaces away from every light. Compensate for
    # that distance with the inverse-square term while keeping the source watt
    # mapping conservative enough to avoid clipped highlights.
    source_value = max(0.3, min(2.0, math.sqrt(energy) / 24.0))
    distance_compensation = max(1.0, model_scale * model_scale)
    return round(min(4000.0, source_value * distance_compensation), 4)


def light_range(light: dict, model_scale: float) -> float:
    cutoff = float(light.get("cutoff_distance") or 0.0)
    if cutoff > 0:
        return round(max(64.0, min(65536.0, cutoff * model_scale)), 3)
    energy = max(0.1, float(light["energy"]))
    return round(
        max(96.0, min(65536.0, math.sqrt(energy) * 20.0 * model_scale)),
        3,
    )


def make_light_clone(
    template: list[str],
    light: dict,
    node_id: int,
    source_center: tuple[float, float, float],
    target_center: tuple[float, float, float],
    cell_size: float,
    layout_scale: float,
    model_scale: float,
    cast_shadow_override: bool | None = None,
) -> list[str]:
    classname = {
        "SPOT": "light_spot",
        "POINT": "light_omni",
        "AREA": "light_rect",
    }[light["type"]]
    block = clone_ids(template, f"light:{light['name']}")
    replace_first_line(block, "nodeID", str(node_id))
    replace_first_line(block, "referenceID", stable_ref(f"light:{light['name']}"))
    replace_first_line(block, "classname", classname)
    set_string_property(block, "color", " ".join(str(value) for value in light["color"]))
    set_string_property(
        block,
        "brightness",
        str(light_brightness(light, model_scale)),
    )
    set_string_property(block, "range", str(light_range(light, model_scale)))
    cast_shadow = (
        light["use_shadow"]
        if cast_shadow_override is None
        else cast_shadow_override
    )
    set_string_property(block, "castshadows", "1" if cast_shadow else "0")
    set_string_property(block, "directlight", "1")
    set_string_property(block, "indirectlight", "1")
    set_string_property(block, "rendertocubemaps", "1")
    if light["type"] == "SPOT":
        set_string_property(block, "outercone", str(light.get("outercone", 45.0)))
        set_string_property(block, "innercone", str(light.get("innercone", 30.0)))
    elif light["type"] == "AREA":
        size = float(light.get("size", 64.0))
        size_y = float(light.get("size_y", size))
        set_string_property(block, "width", str(round(size * model_scale, 3)))
        set_string_property(block, "height", str(round(size_y * model_scale, 3)))
    origin = transform_source_point(
        tuple(light["location"]),
        source_center,
        target_center,
        cell_size,
        layout_scale,
        model_scale,
    )
    replace_last_line(block, "origin", " ".join(f"{value:g}" for value in origin))
    replace_last_line(
        block,
        "angles",
        " ".join(f"{value:g}" for value in light["angles"]),
    )
    return block


def select_active_lights(
    lights: list[dict],
    source_center: tuple[float, float, float],
    target_center: tuple[float, float, float],
    cell_size: float,
    layout_scale: float,
    model_scale: float,
    grid_size: float = 500.0,
    per_bin: int = 4,
) -> tuple[set[str], set[str]]:
    bins: dict[tuple[int, int], list[dict]] = collections.defaultdict(list)
    for light in lights:
        position = transform_source_point(
            tuple(light["location"]),
            source_center,
            target_center,
            cell_size,
            layout_scale,
            model_scale,
        )
        cell = (
            math.floor(position[0] / (grid_size * layout_scale)),
            math.floor(position[1] / (grid_size * layout_scale)),
        )
        bins[cell].append(light)
    active = []
    for candidates in bins.values():
        active.extend(
            sorted(candidates, key=lambda light: light["energy"], reverse=True)[
                :per_bin
            ]
        )
    active_names = {light["name"] for light in active}
    shadow_names = {
        light["name"]
        for light in sorted(active, key=lambda light: light["energy"], reverse=True)[
            :8
        ]
        if light["use_shadow"]
    }
    return active_names, shadow_names


def update_environment(
    lines: list[str],
    sun: dict,
    source_center: tuple[float, float, float],
    target_center: tuple[float, float, float],
) -> None:
    for index, line in enumerate(lines):
        if line.strip() != '"CMapEntity"':
            continue
        end = find_block_end(lines, index)
        body = "\n".join(lines[index : end + 1])
        if '"classname" "string" "light_environment"' not in body:
            continue
        block = lines[index : end + 1]
        set_string_property(
            block, "color", " ".join(str(value) for value in sun["color"])
        )
        set_string_property(
            block,
            "brightness",
            str(round(max(0.5, min(2.0, math.sqrt(float(sun["energy"])) / 14.0)), 4)),
        )
        set_string_property(block, "skycolor", "150 170 205")
        set_string_property(block, "skyintensity", "1.0")
        set_string_property(block, "skytexture", "sky")
        set_string_property(block, "skytexturescale", "1.0")
        set_string_property(block, "skyambientbounce", "82 76 64 255")
        set_string_property(block, "sunlightminbrightness", "64")
        replace_last_line(
            block,
            "angles",
            " ".join(f"{value:g}" for value in sun["angles"]),
        )
        lines[index : end + 1] = block
        return


def update_sky_material(lines: list[str], material: str) -> None:
    old_materials = {
        "materials/skybox/skymodel_hosekwilkie_ref/"
        "skymodel_hosekwilkie_albedo_0_30_turbidity_02_0_elevation_75_0.vmat"
    }
    for index, line in enumerate(lines):
        for old_material in old_materials:
            if old_material in line:
                lines[index] = line.replace(old_material, material)
    for index, line in enumerate(lines):
        if line.strip() != '"CMapEntity"':
            continue
        end = find_block_end(lines, index)
        body = "\n".join(lines[index : end + 1])
        if '"classname" "string" "env_sky"' not in body:
            continue
        block = lines[index : end + 1]
        set_string_property(block, "skyname", material)
        lines[index : end + 1] = block
        return


def update_postprocess(lines: list[str]) -> None:
    for index, line in enumerate(lines):
        if line.strip() != '"CMapEntity"':
            continue
        end = find_block_end(lines, index)
        body = "\n".join(lines[index : end + 1])
        if '"classname" "string" "post_processing_volume"' not in body:
            continue
        block = lines[index : end + 1]
        set_string_property(block, "master", "1")
        set_string_property(block, "enableexposure", "1")
        set_string_property(block, "minexposure", "0.5")
        set_string_property(block, "maxexposure", "2.0")
        set_string_property(block, "exposurecompensation", "0.0")
        lines[index : end + 1] = block
        return


def ambient_fill_lights(
    collision_manifest: dict,
    source_center: tuple[float, float, float],
    target_center: tuple[float, float, float],
    cell_size: float,
    layout_scale: float,
    model_scale: float,
) -> list[dict]:
    grid_size = 800.0 * layout_scale
    bins = collections.defaultdict(list)
    for cell in collision_manifest.get("cells", []):
        origin = transform_cell_origin(
            cell,
            source_center,
            target_center,
            float(cell.get("cell_size", cell_size)),
            layout_scale,
            model_scale,
        )
        center_x = origin[0]
        center_y = origin[1]
        bins[(math.floor(center_x / grid_size), math.floor(center_y / grid_size))].append(
            (center_x, center_y)
        )
    positions = []
    for (grid_x, grid_y), points in sorted(bins.items()):
        center_x = sum(point[0] for point in points) / len(points)
        center_y = sum(point[1] for point in points) / len(points)
        positions.append(
            (
                f"{grid_x}_{grid_y}",
                (
                    center_x,
                    center_y,
                    target_center[2] + 220.0 * model_scale,
                ),
            )
        )
    if not positions:
        positions = [
            (
                "center",
                (
                    target_center[0],
                    target_center[1],
                    target_center[2] + 220.0 * model_scale,
                ),
            )
        ]
    return [
        {
            "name": f"df_ambient_fill_{name}",
            "type": "POINT",
            "location": list(position),
            "energy": 576.0,
            "color": [224, 234, 255],
            "angles": [0.0, 0.0, 0.0],
            "use_shadow": False,
            "cutoff_distance": 3000.0 * model_scale,
        }
        for name, position in positions
    ]


def make_human_scale_reference(
    template: list[str], node_id: int
) -> list[str]:
    spec = PropSpec(
        "human_scale_reference",
        "characters/models/shared/spawn/ctm_spawnpoint.vmdl",
        (640.0, -800.0, 0.0),
        (0.0, 90.0, 0.0),
    )
    block = make_entity_clone(template, spec, node_id)
    replace_first_line(block, "classname", "prop_dynamic")
    set_string_property(block, "solid", "0")
    set_string_property(block, "rendercolor", "255 255 255")
    set_string_property(block, "renderamt", "255")
    set_string_property(block, "disableshadows", "0")
    set_string_property(block, "rendertocubemaps", "true")
    set_string_property(block, "bakelighting", "0")
    set_string_property(block, "renderwithdynamic", "true")
    set_string_property(block, "precomputelightprobes", "false")
    return block


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("template")
    parser.add_argument("smartprop")
    parser.add_argument("manifest")
    parser.add_argument("output")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--limit-cells", type=int, default=0)
    parser.add_argument("--lights")
    parser.add_argument("--light-test", action="store_true")
    parser.add_argument("--collision-manifest")
    parser.add_argument("--remove-background", action="store_true")
    parser.add_argument("--remove-world-walls", action="store_true")
    parser.add_argument("--model-scale", type=float, default=SOURCE_MODEL_SCALE)
    parser.add_argument("--world-scale", type=float, default=SOURCE_LAYOUT_SCALE)
    args = parser.parse_args()
    model_scale = float(args.model_scale)
    layout_scale = float(args.world_scale)
    if not 0.1 <= model_scale <= 200.0:
        parser.error("--model-scale must be between 0.1 and 200.0")
    if not 0.1 <= layout_scale <= 200.0:
        parser.error("--world-scale must be between 0.1 and 200.0")

    template_path = Path(args.template).resolve()
    smartprop_path = Path(args.smartprop).resolve()
    manifest_path = Path(args.manifest).resolve()
    output_path = Path(args.output).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_center = tuple(float(value) for value in manifest["source_center"])
    target_center = tuple(float(value) for value in manifest["target_center"])
    source_cell_size = float(manifest.get("cell_size", 40.0))
    source_cells = manifest["cells"]
    cells = (
        [
            cell
            for cell in source_cells
            if not should_skip_background_geometry(cell)
        ]
        if args.remove_background
        else list(source_cells)
    )
    removed_render_cells = len(source_cells) - len(cells)
    collision_manifest = None
    if args.collision_manifest:
        collision_manifest = json.loads(
            Path(args.collision_manifest).read_text(encoding="utf-8")
        )
        source_collision_cells = collision_manifest["cells"]
        if args.remove_background:
            collision_manifest["cells"] = [
                cell
                for cell in source_collision_cells
                if not should_skip_background_geometry(cell)
            ]
        else:
            collision_manifest["cells"] = list(source_collision_cells)
        removed_collision_cells = len(source_collision_cells) - len(
            collision_manifest["cells"]
        )
    else:
        removed_collision_cells = 0
    if args.preview:
        cells = cells[:1]
    elif args.limit_cells > 0:
        cells = cells[: args.limit_cells]

    lines = template_path.read_text(encoding="utf-8", errors="replace").splitlines()
    mesh_start = next(
        index for index, line in enumerate(lines) if line.strip() == '"CMapMesh"'
    )
    mesh_end = find_block_end(lines, mesh_start)
    mesh_template = lines[mesh_start : mesh_end + 1]
    if not mesh_template[-1].rstrip().endswith(","):
        mesh_template[-1] = mesh_template[-1].rstrip() + ","

    max_node_id = max(
        int(match.group(1))
        for match in (
            __import__("re").search(r'"nodeID" "int" "(\d+)"', line) for line in lines
        )
        if match
    )
    prop_template = extract_prop_static_template(smartprop_path)
    light_template = extract_class_template(
        template_path, "light_environment"
    )
    update_sky_material(lines, "materials/skybox/sky_de_dust2.vmat")
    update_postprocess(lines)

    scaled_cell_origins = [
        transform_cell_origin(
            cell,
            source_center,
            target_center,
            source_cell_size,
            layout_scale,
            model_scale,
        )
        for cell in cells
    ]
    cell_padding = source_cell_size * model_scale
    min_x = min(position[0] for position in scaled_cell_origins) - cell_padding
    max_x = max(position[0] for position in scaled_cell_origins) + cell_padding
    min_y = min(position[1] for position in scaled_cell_origins) - cell_padding
    max_y = max(position[1] for position in scaled_cell_origins) + cell_padding
    wall_thickness = max(128.0, 4.0 * layout_scale)
    wall_height = max(4096.0, 128.0 * model_scale)
    world_walls = [
        BoxSpec(
            "full_wall_west",
            (min_x, (min_y + max_y) * 0.5, wall_height * 0.5),
            (wall_thickness, max_y - min_y, wall_height),
            CONCRETE_DARK,
        ),
        BoxSpec(
            "full_wall_east",
            (max_x, (min_y + max_y) * 0.5, wall_height * 0.5),
            (wall_thickness, max_y - min_y, wall_height),
            CONCRETE_DARK,
        ),
        BoxSpec(
            "full_wall_south",
            ((min_x + max_x) * 0.5, min_y, wall_height * 0.5),
            (max_x - min_x, wall_thickness, wall_height),
            CONCRETE_DARK,
        ),
        BoxSpec(
            "full_wall_north",
            ((min_x + max_x) * 0.5, max_y, wall_height * 0.5),
            (max_x - min_x, wall_thickness, wall_height),
            CONCRETE_DARK,
        ),
    ]
    if args.remove_world_walls:
        world_walls = []
    boxes = [
        *make_floor_tiles(),
        *make_human_scale_mannequin(),
        *world_walls,
    ]

    inserted = []
    next_node_id = max_node_id + 1
    collision_count = 0
    for cell in cells:
        spec = PropSpec(
            f"full_{cell['name']}",
            cell["vmdl"],
            transform_cell_origin(
                cell,
                source_center,
                target_center,
                source_cell_size,
                layout_scale,
                model_scale,
            ),
            (0, 0, 0),
            (model_scale,) * 3,
        )
        cell_entity = make_entity_clone(prop_template, spec, next_node_id)
        set_string_property(cell_entity, "solid", "0")
        set_string_property(cell_entity, "bakelighting", "0")
        set_string_property(cell_entity, "renderwithdynamic", "true")
        set_string_property(cell_entity, "precomputelightprobes", "false")
        inserted.extend(cell_entity)
        next_node_id += 1
    inserted.extend(make_human_scale_reference(prop_template, next_node_id))
    next_node_id += 1
    if args.lights:
        lighting = json.loads(Path(args.lights).read_text(encoding="utf-8"))
        lights = [
            light
            for light in lighting["lights"]
            if light["type"] in {"SPOT", "POINT", "AREA"} and not light["hide_render"]
        ]
        if args.light_test:
            lights = [
                next(light for light in lights if light["type"] == light_type)
                for light_type in ("SPOT", "POINT", "AREA")
            ]
        active_light_names, shadow_light_names = select_active_lights(
            lights,
            source_center,
            target_center,
            source_cell_size,
            layout_scale,
            model_scale,
        )
        for light in lights:
            if light["name"] not in active_light_names:
                continue
            light_block = make_light_clone(
                light_template,
                light,
                next_node_id,
                source_center,
                target_center,
                source_cell_size,
                layout_scale,
                model_scale,
                cast_shadow_override=light["name"] in shadow_light_names,
            )
            set_string_property(
                light_block,
                "enabled",
                "1",
            )
            inserted.extend(light_block)
            next_node_id += 1
        suns = [
            light
            for light in lighting["lights"]
            if light["type"] == "SUN" and not light["hide_render"]
        ]
        if suns:
            update_environment(
                lines,
                suns[0],
                source_center,
                target_center,
            )
        for fill_light in ambient_fill_lights(
            collision_manifest,
            source_center,
            target_center,
            source_cell_size,
            layout_scale,
            model_scale,
        ):
            fill_block = make_light_clone(
                light_template,
                fill_light,
                next_node_id,
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0),
                source_cell_size,
                layout_scale,
                model_scale,
            )
            set_string_property(fill_block, "brightness", "1.8")
            set_string_property(
                fill_block,
                "range",
                str(round(1400.0 * model_scale)),
            )
            set_string_property(fill_block, "castshadows", "0")
            set_string_property(fill_block, "directlight", "1")
            set_string_property(fill_block, "indirectlight", "1")
            inserted.extend(fill_block)
            next_node_id += 1
    if collision_manifest:
        collision_size = float(collision_manifest.get("cell_size", 80.0))
        scaled_collision_size = collision_size * model_scale
        skipped_collision_cells = {
            "cell_176_142",
            "cell_47_49",
            "cell_64_79",
            "cell_61_64",
        }
        for collision_cell in collision_manifest["cells"]:
            if collision_cell["name"] in skipped_collision_cells:
                continue
            origin = transform_cell_origin(
                collision_cell,
                source_center,
                target_center,
                collision_size,
                layout_scale,
                model_scale,
            )
            origin_x, origin_y, _ = origin
            overlaps_spawn_clear_zone = (
                origin_x + scaled_collision_size > -450
                and origin_x < 1450
                and origin_y + scaled_collision_size > -1400
                and origin_y < -400
            )
            if overlaps_spawn_clear_zone:
                continue
            spec = PropSpec(
                f"collision_{collision_cell['name']}",
                collision_cell["vmdl"],
                origin,
                (0, 0, 0),
                (model_scale,) * 3,
            )
            collision_entity = make_entity_clone(
                prop_template, spec, next_node_id
            )
            set_string_property(collision_entity, "renderamt", "0")
            set_string_property(collision_entity, "rendercolor", "0 0 0")
            set_string_property(collision_entity, "solid", "6")
            set_string_property(collision_entity, "bakelighting", "0")
            set_string_property(collision_entity, "renderwithdynamic", "false")
            set_string_property(collision_entity, "precomputelightprobes", "false")
            inserted.extend(collision_entity)
            next_node_id += 1
            collision_count += 1
    for spec in boxes:
        inserted.extend(make_mesh_clone(mesh_template, spec, next_node_id))
        next_node_id += 1

    lines[mesh_start:mesh_start] = inserted
    lines = modify_worldtext_blocks(lines)
    relocate_spawns(lines)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"WROTE={output_path} CELL_PROPS={len(cells)} BOXES={len(boxes)} "
        f"LIGHTS={0 if not args.lights else len(lights)} "
        f"COLLISION_PROPS={collision_count} "
        f"REMOVED_RENDER_CELLS={removed_render_cells} "
        f"REMOVED_COLLISION_CELLS={removed_collision_cells} "
        f"MAX_NODE_ID={next_node_id - 1}"
    )


if __name__ == "__main__":
    main()
