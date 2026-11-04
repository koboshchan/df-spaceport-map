"""Compare the active Spaceport map's asset references with its export manifests."""

import argparse
import json
import re
from pathlib import Path
from spaceport_collision_rules import collision_candidate


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def references(path, pattern):
    return {match.decode("ascii") + "_c" for match in re.findall(pattern, path.read_bytes())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("vmap", "addon", "inventory", "render", "collision", "supplement", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()

    models = set(re.findall(r'"model" "string" "([^"]+\.vmdl)"', args.vmap.read_text(encoding="utf-8-sig")))
    render_cells = [cell for cell in read_json(args.render)["cells"] if cell["vmdl"] in models]
    render_objects = {name for cell in render_cells for name in cell["object_names"]}
    physics_objects = {
        name
        for cell in read_json(args.collision)["cells"]
        if cell["vmdl"].replace("/c/", "/physics/") in models or cell["vmdl"] in models
        for name in cell["object_names"]
    }
    physics_objects.update(
        item["name"]
        for cell in read_json(args.supplement)["cells"]
        if cell["model"] in models
        for item in cell["objects"]
    )
    materials = set()
    missing_models = []
    for model in sorted(models):
        compiled = args.addon / (model + "_c")
        if compiled.is_file():
            materials.update(references(compiled, rb"materials/df_full_v2/m/[a-z0-9]+\.vmat"))
        else:
            missing_models.append(model + "_c")
    missing_materials = []
    missing_textures = {}
    for material in sorted(materials):
        compiled = args.addon / material
        if not compiled.is_file():
            missing_materials.append(material)
            continue
        absent = sorted(
            texture for texture in references(compiled, rb"materials/df_full_v2/t/[a-zA-Z0-9_.-]+\.vtex")
            if not (args.addon / texture).is_file()
        )
        if absent:
            missing_textures[material] = absent

    mesh_objects = [obj for obj in read_json(args.inventory)["objects"] if obj["type"] == "MESH"]
    source_objects = {obj["name"] for obj in mesh_objects}
    unlisted_objects = render_objects - physics_objects
    collision_candidates = {
        obj["name"] for obj in mesh_objects
        if obj["name"] in unlisted_objects and collision_candidate(obj)
    }
    lab_objects = {
        obj["name"] for obj in mesh_objects
        if any("SpaceCenterH2" in name for name in obj["collections"])
    }
    report = {
        "render_cells": len(render_cells),
        "render_objects": len(render_objects),
        "source_objects_outside_active_render_cells": sorted(source_objects - render_objects),
        "objects_listed_in_physics_manifests": len(render_objects & physics_objects),
        "material_references": len(materials),
        "missing_loose_models": missing_models,
        "missing_loose_materials": missing_materials,
        "missing_loose_texture_references": missing_textures,
        "render_objects_without_manifest_collision": sorted(unlisted_objects),
        "unlisted_collision_candidates": sorted(collision_candidates),
        "lab_unlisted_collision_candidates": sorted(collision_candidates & lab_objects),
        "lab_source_objects": len(lab_objects),
        "lab_objects_missing_from_active_render_cells": sorted(lab_objects - render_objects),
        "lab_render_objects_without_manifest_collision": sorted((lab_objects & render_objects) - physics_objects),
    }
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: len(value) if isinstance(value, (dict, list)) else value for key, value in report.items()}))


if __name__ == "__main__":
    main()
