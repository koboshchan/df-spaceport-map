"""Add physics-only props for solid assets missing from the Spaceport VMap."""

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_df_collision_only import physics_only_model
from build_df_player_scale import place, world
from build_df_spaceport import clone_ids, replace_first_line, replace_last_line
from export_scene_cells import write_vmdl
from spaceport_collision_rules import COLLISION_NAME_RE, NO_COLLISION, collision_candidate
from tune_df_raytrace import ENTITY, PROPERTIES, STRING


CELL_SIZE = 80
MODEL_PREFIX = "models/df_collision_extra/c"
CLOSED_BOX = re.compile(r"SupplyBox|PackingBox|PlasticBox|Crate", re.I)
OPEN_BOX = re.compile(r"open|broken|damage|lid|cover|stack|pile|rack|empty", re.I)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def active_objects(manifest, vmap):
    models = set(re.findall(r'"model" "string" "([^"]+)"', vmap))
    return {
        name
        for cell in manifest["cells"]
        if cell["vmdl"] in models or cell["vmdl"].replace("/c/", "/physics/") in models
        for name in cell["object_names"]
    }


def select_objects(inventory, missing):
    return (record for record in inventory["objects"]
            if record["name"] in missing and collision_candidate(record))


def box_geometry(obj):
    from mathutils import Vector

    corners = tuple(Vector(point) for point in obj.bound_box)
    faces = ((3, 7, 4, 0), (5, 6, 2, 1), (4, 5, 1, 0),
             (2, 6, 7, 3), (1, 2, 3, 0), (7, 6, 5, 4))
    return corners, tuple(triangle for a, b, c, d in faces for triangle in ((a, b, c), (a, c, d)))


def mesh_geometry(obj, depsgraph, cache, scratch):
    blocked = tuple(
        i for i, slot in enumerate(obj.material_slots)
        if slot.material and NO_COLLISION.search(slot.material.name)
    )
    limit = 1536 if COLLISION_NAME_RE.search(obj.name) else 512
    key = (obj.data.name, obj.name if obj.modifiers else None, blocked, limit)
    if key in cache:
        return cache[key]

    evaluated = obj.evaluated_get(depsgraph)
    bm = bmesh.new()
    try:
        try:
            bm.from_mesh(evaluated.to_mesh())
        finally:
            evaluated.to_mesh_clear()
        bmesh.ops.delete(
            bm, geom=[face for face in bm.faces if face.material_index in blocked], context="FACES"
        )
        bmesh.ops.dissolve_limit(
            bm, angle_limit=math.radians(4), verts=list(bm.verts), edges=list(bm.edges)
        )
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        if len(bm.faces) > limit:
            bm.to_mesh(scratch.data)
            scratch.data.update()
            scratch.modifiers[0].ratio = limit / len(bm.faces)
            depsgraph.update()
            reduced = scratch.evaluated_get(depsgraph)
            reduced_mesh = reduced.to_mesh()
            try:
                reduced_mesh.calc_loop_triangles()
                cache[key] = (
                    tuple(vert.co.copy() for vert in reduced_mesh.vertices),
                    tuple(tuple(tri.vertices) for tri in reduced_mesh.loop_triangles),
                )
            finally:
                reduced.to_mesh_clear()
        else:
            bm.verts.index_update()
            cache[key] = (
                tuple(vert.co.copy() for vert in bm.verts),
                tuple(tuple(vert.index for vert in face.verts) for face in bm.faces),
            )
    finally:
        bm.free()
    return cache[key]


def export_cells(records, output, model_prefix):
    groups = defaultdict(list)
    for record in records:
        bounds = record["bounds"]
        grid = tuple(math.floor((a + b) / (2 * CELL_SIZE)) for a, b in zip(bounds["min"][:2], bounds["max"][:2]))
        groups[grid].append(record)
    root = output / model_prefix
    root.mkdir(parents=True, exist_ok=True)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cache = {}
    seen = set()
    bpy.ops.object.select_all(action="DESELECT")
    scratch_mesh = bpy.data.meshes.new("DF_CollisionScratch")
    scratch = bpy.data.objects.new("DF_CollisionScratch", scratch_mesh)
    bpy.context.scene.collection.objects.link(scratch)
    scratch.modifiers.new("Simplify", "DECIMATE").use_collapse_triangulate = True
    depsgraph.update()
    for gx, gy in sorted(groups):
        name = f"cell_{gx}_{gy}"
        origin = (gx * CELL_SIZE, gy * CELL_SIZE, 0)
        vertices, faces, included = [], [], []
        for record in groups[gx, gy]:
            obj = bpy.data.objects[record["name"]]
            matrix = obj.matrix_world.copy()
            stamp = (obj.data.name, tuple(round(v, 5) for row in matrix for v in row))
            if stamp in seen:
                continue
            seen.add(stamp)
            closed_box = CLOSED_BOX.search(obj.name) and not OPEN_BOX.search(obj.name)
            local_verts, local_faces = (
                box_geometry(obj) if closed_box else mesh_geometry(obj, depsgraph, cache, scratch)
            )
            if not local_faces:
                continue
            start = len(vertices)
            for vertex in local_verts:
                x, y, z = matrix @ vertex
                vertices.append((y - origin[1], origin[0] - x, z))
            mirrored = matrix.to_3x3().determinant() < 0
            faces.extend(tuple(start + i for i in (face[::-1] if mirrored else face)) for face in local_faces)
            included.append({
                "name": obj.name, "geometry": "box" if closed_box else "mesh",
                "bounds": record["bounds"], "triangles": len(local_faces),
            })
        if not faces:
            continue
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.validate()
        proxy = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(proxy)
        proxy.select_set(True)
        bpy.context.view_layer.objects.active = proxy
        fbx = root / f"{name}.fbx"
        try:
            bpy.ops.export_scene.fbx(
                filepath=str(fbx), use_selection=True, object_types={"MESH"},
                apply_scale_options="FBX_SCALE_ALL", mesh_smooth_type="FACE",
                bake_anim=False, add_leaf_bones=False,
            )
        finally:
            bpy.data.objects.remove(proxy, do_unlink=True)
            bpy.data.meshes.remove(mesh)
        model = write_vmdl(root, name, model_prefix)
        model_path = output / model
        model_path.write_text(
            physics_only_model(model_path.read_text(encoding="utf-8"), f"{model_prefix}/{name}.fbx"),
            encoding="utf-8",
        )
        yield {"model": model, "origin": origin, "objects": included, "triangles": len(faces)}
    bpy.data.objects.remove(scratch, do_unlink=True)
    bpy.data.meshes.remove(scratch_mesh)


def add_colliders(vmap, cells):
    def is_collision(match):
        props = dict(STRING.findall(PROPERTIES.search(match[0])[0]))
        return props.get("model", "").startswith("models/df_collision80/physics/")

    template = next(match for match in ENTITY.finditer(vmap) if is_collision(match))
    next_id = max(map(int, re.findall(r'"nodeID" "int" "(\d+)"', vmap))) + 1
    entities = []
    for node_id, cell in enumerate(cells, next_id):
        block = clone_ids(template[0].splitlines(), f"collision-supplement:{cell['model']}")
        replace_first_line(block, "nodeID", str(node_id))
        replace_first_line(block, "referenceID", f"0x{node_id:016x}")
        replace_last_line(block, "model", cell["model"])
        replace_last_line(block, "disableshadows", "1")
        place(block, world(cell["origin"]))
        entities.append("\n".join(block))
    return vmap[:template.end()] + ",\n" + ",\n".join(entities) + vmap[template.end():]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inventory", "render_manifest", "collision_manifest", "vmap", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--existing-supplement", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    vmap = args.vmap.read_text(encoding="utf-8-sig")
    existing = read_json(args.existing_supplement)["cells"] if args.existing_supplement else []
    existing_models = {cell["model"] for cell in existing}
    active_models = set(re.findall(r'"model" "string" "([^"]+)"', vmap))
    if existing_models != {model for model in active_models if model.startswith(MODEL_PREFIX + "/")}:
        parser.error("the existing supplement must describe every supplemental model in the VMap")
    missing = active_objects(read_json(args.render_manifest), vmap) - active_objects(
        read_json(args.collision_manifest), vmap
    )
    missing.difference_update(item["name"] for cell in existing for item in cell["objects"])
    selected = list(select_objects(read_json(args.inventory), missing))
    print(f"Selected {len(selected)} supplemental objects", flush=True)
    model_prefix = f"{MODEL_PREFIX}/followup" if existing else MODEL_PREFIX
    cells = list(export_cells(selected, args.output, model_prefix))
    if not cells:
        raise ValueError("No supplemental collision models were generated")
    combined = existing + cells
    counts = Counter(obj["geometry"] for cell in combined for obj in cell["objects"])
    (args.output / "collision_supplement.json").write_text(
        json.dumps({"cells": combined, "counts": counts}, indent=2), encoding="utf-8"
    )
    (args.output / args.vmap.name).write_text(add_colliders(vmap, cells), encoding="utf-8")
    print(f"Collision tiles: {len(cells)}; objects: {dict(counts)}; triangles: {sum(c['triangles'] for c in cells)}")


if __name__ == "__main__":
    main()
