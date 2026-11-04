"""Build a player-scale spaceport slice from the relit open VMap and cell exports."""
from __future__ import annotations

import argparse
import itertools
import json
import re
from pathlib import Path

from build_df_full import should_skip_background_geometry
from build_df_spaceport import clone_ids, find_block_end, replace_first_line, replace_last_line

SCALE = 36
SOURCE_ORIGIN = (6694, 4578, -223.69)
PLAY_RADIUS = (300, 280)
CELL_MODEL = re.compile(r'"model" "string" "(models/(?:df_full40|df_collision80)/c/[^"]+)"')


def world(point):
    return tuple((value - anchor) * SCALE for value, anchor in zip(point, SOURCE_ORIGIN))


def origin(block):
    return tuple(map(float, re.findall(r'"origin" "vector3" "([^"]+)"', "\n".join(block))[-1].split()))


def place(block, point):
    replace_last_line(block, "origin", " ".join(f"{value:.6f}" for value in point))


def in_play_area(point, padding=0):
    return all(abs(point[i] - SOURCE_ORIGIN[i]) <= PLAY_RADIUS[i] + padding for i in range(2))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def cell_positions(manifest):
    size = manifest["cell_size"]
    return {
        cell["vmdl"]: world(cell["cell_origin_blender"])
        for cell in manifest["cells"]
        if not should_skip_background_geometry(cell)
        and in_play_area(tuple(v + size / 2 for v in cell["cell_origin_blender"][:2]))
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "render", "collision", "ground", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    render_manifest = read_json(args.render)
    render_positions = cell_positions(render_manifest)
    collision_positions = cell_positions(read_json(args.collision))
    ground = read_json(args.ground)
    spawns = {team: iter(ground[team]) for team in ("ct", "t")}
    spawn_counts = {"ct": 0, "t": 0}
    destinations = {
        "96 -320 32": ground["ct"][0],
        "944 -320 32": ground["t"][0],
        "256 640 32": ground["a"][0],
        "768 640 32": ground["b"][0],
    }
    fills = iter(itertools.product((6620, 6694, 6770), (4488, 4578, 4670)))
    source_center = render_manifest["source_center"]
    old_target = render_manifest["target_center"]
    lines = args.baseline.read_text(encoding="utf-8-sig").splitlines()
    next_id = 1 + max(int(n) for n in re.findall(r'"nodeID" "int" "(\d+)"', "\n".join(lines)))
    kept_models = set()
    collision_template = None
    collision_insert = None
    output = []
    i = 0
    while i < len(lines):
        kind = lines[i].strip()
        if kind not in {'"CMapEntity"', '"CMapMesh"'}:
            output.append(lines[i])
            i += 1
            continue
        end = find_block_end(lines, i)
        block = lines[i:end+1]
        i = end + 1
        text = "\n".join(block)
        model = CELL_MODEL.search(text)
        classname = re.search(r'"classname" "string" "([^"]+)"', text)
        classname = classname[1] if classname else None
        if model:
            model = model[1]
            is_collision = model in collision_positions
            if "df_collision80" in model:
                collision_template = block
                collision_insert = len(output)
            if model not in render_positions and not is_collision:
                continue
            place(block, collision_positions[model] if is_collision else render_positions[model])
            replace_last_line(block, "scales", f"{SCALE} {SCALE} {SCALE}")
            kept_models.add(model)
        elif kind == '"CMapMesh"':
            if 'materials/tools/toolstrigger.vmat' not in text:
                continue
            old = " ".join(f"{v:g}" for v in origin(block))
            p = world(destinations[old])
            place(block, (p[0], p[1], p[2] + 32))
        elif classname in ("func_bomb_target", "func_buyzone"):
            old = " ".join(f"{v:g}" for v in origin(block))
            p = world(destinations[old])
            for index,line in enumerate(block):
                if re.match(r'^\s*"origin" "vector3"',line):
                    indent = line[:len(line)-len(line.lstrip())]
                    block[index] = f'{indent}"origin" "vector3" "{p[0]:.6f} {p[1]:.6f} {p[2]+32:.6f}"'
        elif classname in ("info_player_counterterrorist", "info_player_terrorist"):
            team = "ct" if classname == "info_player_counterterrorist" else "t"
            x,y,z = world(next(spawns[team]))
            place(block,(x,y,z+8))
            replace_last_line(block, "angles", "0 54 0" if team == "ct" else "0 234 0")
            spawn_counts[team] += 1
        elif classname == "light_omni2":
            x,y = next(fills)
            place(block, world((x,y,-205)))
            replace_last_line(block,"range","4200")
        elif classname in ("light_omni", "light_rect", "light_spot"):
            point = tuple(v - t + s for v,t,s in zip(origin(block),old_target,source_center))
            if not in_play_area(point,40):
                continue
            place(block, world(point))
        elif classname in ("point_worldtext", "prop_static"):
            continue
        output.extend(block)
    assert spawn_counts == {"ct":16,"t":16}
    assert collision_template is not None and collision_insert is not None
    added = []
    for model,point in collision_positions.items():
        if model in kept_models:
            continue
        block = clone_ids(collision_template, f"player-scale:{model}")
        replace_first_line(block, "nodeID", str(next_id))
        replace_first_line(block, "referenceID", f"0x{next_id:016x}")
        replace_last_line(block, "model", model)
        place(block,point)
        replace_last_line(block,"scales",f"{SCALE} {SCALE} {SCALE}")
        added.extend(block)
        next_id += 1
    output[collision_insert:collision_insert] = added
    for index in range(1, len(output)):
        if output[index].strip() == "]" and output[index - 1].strip() == "},":
            output[index - 1] = output[index - 1].rstrip().removesuffix(",")
    args.output.write_text("\n".join(output)+"\n",encoding="utf-8")
    print(f"Render cells {len(kept_models & render_positions.keys())}, collision cells {len(collision_positions)}, spawns {spawn_counts}")


if __name__ == "__main__":
    main()
