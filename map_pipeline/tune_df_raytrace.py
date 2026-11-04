"""Prepare the Spaceport service-road and workshop for Source 2 light baking."""

import argparse
import re
from pathlib import Path

from build_df_spaceport import clone_ids, replace_first_line, replace_last_line


ENTITY = re.compile(r'(?m)^\t{3}"CMapEntity"\n\t{3}\{.*?^\t{3}\}(?=,?\n)', re.S)
PROPERTIES = re.compile(r'"entity_properties" "EditGameClassProps"\s*\{[^{}]*\}')
STRING = re.compile(r'"([^"]+)" "string" "([^"]*)"')
ORIGIN = re.compile(r'"origin" "vector3" "([^"]+)"')
RENDER_CELL = re.compile(r'models/df_full40/c/cell_(\d+)_(\d+)\.vmdl')
PRACTICAL_LIGHTS = {"light_spot", "light_rect", "light_omni"}
SETTINGS = {
    "light_environment": {
        "color": "255 236 213",
        "brightness": "2.6",
        "castshadows": "1",
        "directlight": "3",
        "indirectlight": "1",
        "angulardiameter": "1.0",
        "skytexturescale": "0.8",
        "skyambientbounce": "94 82 65 255",
        "baked_light_indexing": "1",
        "minroughness": "0.14",
    },
    "env_cubemap_fog": {
        "StartDisabled": "0",
        "cubemapfogstartdistance": "1900",
        "cubemapfogenddistance": "14500",
        "cubemapfogfalloffexponent": "1.7",
        "cubemapfogmaxopacity": "0.18",
    },
    "post_processing_volume": {
        "exposurecompensation": "0.05",
        "minexposure": "0.8",
        "maxexposure": "1.6",
    },
    "light_omni2": {"brightness_legacy": "0.55", "indirectlight": "0"},
}


def patch_properties(entity, changes):
    props = PROPERTIES.search(entity)
    existing = dict(STRING.findall(props[0]))
    if missing := changes.keys() - existing.keys():
        raise ValueError(f"{existing['classname']} is missing {sorted(missing)}")
    updated = STRING.sub(
        lambda m: f'"{m[1]}" "string" "{changes[m[1]]}"' if m[1] in changes else m[0],
        props[0],
    )
    return entity[:props.start()] + updated + entity[props.end():]


def probe(template, node_id, name, origin, mins, maxs, spacing, priority):
    lines = clone_ids(template.splitlines(), f"df-raytrace:{name}")
    replace_first_line(lines, "nodeID", str(node_id))
    replace_first_line(lines, "referenceID", f"0x{node_id:016x}")
    replace_last_line(lines, "origin", origin)
    entity = "\n".join(lines)
    props = PROPERTIES.search(entity)
    prop_id = re.search(r'"id" "elementid" "[^"]+"', props[0])[0]
    values = {
        "classname": "env_combined_light_probe_volume",
        "targetname": name,
        "StartDisabled": "0",
        "box_mins": mins,
        "box_maxs": maxs,
        "voxel_size": spacing,
        "flood_fill": "1",
        "voxelize": "1",
        "indoor_outdoor_level": priority,
        "edge_fade_dists": "64 64 32",
        "bakefarz": "5500",
    }
    lines = [prop_id, *(f'"{key}" "string" "{value}"' for key, value in values.items())]
    updated = '"entity_properties" "EditGameClassProps"\n\t\t\t\t{\n'
    updated += "\n".join("\t" * 5 + line for line in lines) + "\n\t\t\t\t}"
    return entity[:props.start()] + updated + entity[props.end():]


def build(source, core_only=False):
    selected = set()
    light_count = 0
    next_node_id = max(map(int, re.findall(r'"nodeID" "int" "(\d+)"', source))) + 1

    def relight(match):
        nonlocal light_count
        entity = match[0]
        props = dict(STRING.findall(PROPERTIES.search(entity)[0]))
        classname = props["classname"]
        if classname == "env_sky":
            return entity + ",\n" + probe(
                entity, next_node_id, "df_service_road_probe", "3060 2010 88",
                "-1430 -1600 -175", "1510 1510 720", "108", "0",
            ) + ",\n" + probe(
                entity, next_node_id + 1, "df_workshop_probe", "3636 3673 95",
                "-360 -390 -105", "475 410 240", "48", "1",
            )
        if classname == "prop_static":
            cell = RENDER_CELL.fullmatch(props["model"])
            if not cell:
                return entity
            x, y = map(int, cell.groups())
            if 168 <= x <= 171 and 115 <= y <= 118:
                selected.add((x, y))
                return patch_properties(entity, {
                    "bakelighting": "1",
                    "lightmapscalebias": "-2",
                    "disableshadows": "3",
                    "renderwithdynamic": "false",
                })
            if core_only:
                return ""
            return patch_properties(entity, {
                "classname": "prop_dynamic",
                "solid": "0",
                "disableshadows": "1",
            })
        if classname in PRACTICAL_LIGHTS:
            x, y, z = map(float, ORIGIN.findall(entity)[-1].split())
            in_route = 1000 <= x <= 6100 and 650 <= y <= 5600 and -40 <= z <= 625
            use_for_bake = in_route and float(props["brightness"]) >= 1.2
            if use_for_bake:
                light_count += 1
            if not core_only or not use_for_bake:
                # Their illumination is in the lightmaps. Legacy entities can still
                # request dynamic shadow slots when present in the runtime lump.
                return ""
            return patch_properties(entity, {"range": "220", "bouncescale": "0.65"})
        if classname in SETTINGS:
            return patch_properties(entity, SETTINGS[classname])
        return entity

    result = ENTITY.sub(relight, source)
    result = re.sub(r"(?m)^,\n", "", result)
    if len(selected) != 16 or not light_count or result.count('"env_combined_light_probe_volume"') != 2:
        raise ValueError(f"Unexpected source layout: {len(selected)} core cells, {light_count} practical lights")
    print(f"{len(selected)} lightmapped cells, {light_count} baked practical lights, 2 combined probe volumes")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--core-only", action="store_true", help="Omit peripheral render cells during the light bake")
    args = parser.parse_args()
    args.output.write_text(build(args.source.read_text(encoding="utf-8-sig"), args.core_only), encoding="utf-8")


if __name__ == "__main__":
    main()
