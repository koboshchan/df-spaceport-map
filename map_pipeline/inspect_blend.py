import json
import math
import os
import sys
import time
from collections import Counter, defaultdict

import bpy
from mathutils import Vector


def world_bounds(obj):
    if obj.type not in {"MESH", "CURVE", "SURFACE", "META", "FONT"}:
        return None
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = [min(point[i] for point in points) for i in range(3)]
    high = [max(point[i] for point in points) for i in range(3)]
    return {
        "min": [round(value, 4) for value in low],
        "max": [round(value, 4) for value in high],
        "size": [round(high[i] - low[i], 4) for i in range(3)],
    }


def mesh_stats(obj):
    mesh = obj.data
    if obj.type != "MESH" or mesh is None:
        return None
    triangle_count = 0
    mesh.calc_loop_triangles()
    triangle_count = len(mesh.loop_triangles)
    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "triangles": triangle_count,
        "materials": len(mesh.materials),
        "uv_layers": len(mesh.uv_layers),
        "color_attributes": len(mesh.color_attributes),
        "shape_keys": len(mesh.shape_keys.key_blocks) if mesh.shape_keys else 0,
    }


def object_record(obj):
    mesh = mesh_stats(obj)
    modifiers = Counter(modifier.type for modifier in obj.modifiers)
    return {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "collections": [collection.name for collection in obj.users_collection],
        "hidden_viewport": obj.hide_viewport,
        "hidden_render": obj.hide_render,
        "location": [round(value, 4) for value in obj.location],
        "rotation": [round(value, 4) for value in obj.rotation_euler],
        "scale": [round(value, 4) for value in obj.scale],
        "bounds": world_bounds(obj),
        "mesh": mesh,
        "modifiers": dict(modifiers),
        "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
    }


def collection_record(collection, level=0):
    return {
        "name": collection.name,
        "level": level,
        "objects": len(collection.objects),
        "children": len(collection.children),
        "hide_viewport": collection.hide_viewport,
        "hide_render": collection.hide_render,
    }


def main():
    started = time.time()
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not args:
        raise SystemExit("usage: inspect_blend.py -- <output.json>")
    output_path = os.path.abspath(args[0])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    object_types = Counter(obj.type for obj in bpy.data.objects)
    object_records = [object_record(obj) for obj in bpy.data.objects]
    mesh_records = [record for record in object_records if record["mesh"]]
    mesh_records.sort(
        key=lambda record: (
            record["mesh"]["triangles"],
            math.prod(record["bounds"]["size"]) if record["bounds"] else 0,
        ),
        reverse=True,
    )

    total_vertices = sum(record["mesh"]["vertices"] for record in mesh_records)
    total_triangles = sum(record["mesh"]["triangles"] for record in mesh_records)
    material_usage = Counter(
        material
        for record in mesh_records
        for material in record["materials"]
        if material
    )

    image_records = []
    packed_image_bytes = 0
    for image in bpy.data.images:
        packed_size = getattr(image.packed_file, "size", 0) if image.packed_file else 0
        packed_image_bytes += packed_size
        image_records.append(
            {
                "name": image.name,
                "source": image.source,
                "filepath": bpy.path.abspath(image.filepath) if image.filepath else "",
                "packed": bool(image.packed_file),
                "packed_size": packed_size,
                "size": list(image.size),
                "has_data": image.has_data,
            }
        )

    material_records = []
    for material in bpy.data.materials:
        images = []
        nodes = []
        if material.use_nodes and material.node_tree:
            for node in material.node_tree.nodes:
                nodes.append({"name": node.name, "type": node.type})
                if node.type == "TEX_IMAGE" and node.image:
                    images.append(node.image.name)
        material_records.append(
            {
                "name": material.name,
                "users": material.users,
                "use_nodes": material.use_nodes,
                "blend_method": getattr(material, "surface_render_method", None),
                "images": sorted(set(images)),
                "nodes": nodes,
            }
        )

    collections = [collection_record(collection) for collection in bpy.data.collections]
    scene_bounds = None
    bounds = [record["bounds"] for record in mesh_records if record["bounds"]]
    if bounds:
        scene_bounds = {
            "min": [min(item["min"][i] for item in bounds) for i in range(3)],
            "max": [max(item["max"][i] for item in bounds) for i in range(3)],
        }
        scene_bounds["size"] = [
            scene_bounds["max"][i] - scene_bounds["min"][i] for i in range(3)
        ]
        scene_bounds = {
            key: [round(value, 4) for value in values]
            for key, values in scene_bounds.items()
        }

    scenes = []
    for scene in bpy.data.scenes:
        scenes.append(
            {
                "name": scene.name,
                "unit_system": scene.unit_settings.system,
                "unit_scale": scene.unit_settings.scale_length,
                "length_unit": scene.unit_settings.length_unit,
                "objects": len(scene.objects),
                "camera": scene.camera.name if scene.camera else None,
                "frame_start": scene.frame_start,
                "frame_end": scene.frame_end,
                "render_engine": scene.render.engine,
                "world": scene.world.name if scene.world else None,
            }
        )

    report = {
        "source_blend": bpy.data.filepath,
        "blender_version": bpy.app.version_string,
        "file_size": os.path.getsize(bpy.data.filepath),
        "duration_seconds": None,
        "scenes": scenes,
        "active_scene": bpy.context.scene.name,
        "object_types": dict(object_types),
        "object_count": len(bpy.data.objects),
        "mesh_object_count": len(mesh_records),
        "total_vertices": total_vertices,
        "total_triangles": total_triangles,
        "scene_bounds": scene_bounds,
        "collections": collections,
        "materials": {
            "count": len(material_records),
            "records": material_records,
            "usage": dict(material_usage.most_common()),
        },
        "images": {
            "count": len(image_records),
            "packed_count": sum(record["packed"] for record in image_records),
            "packed_bytes": packed_image_bytes,
            "records": image_records,
        },
        "libraries": [
            {
                "name": library.name,
                "filepath": bpy.path.abspath(library.filepath),
                "users": library.users,
            }
            for library in bpy.data.libraries
        ],
        "objects": object_records,
        "largest_meshes": mesh_records[:100],
        "warnings": list(bpy.context.scene.get("warnings", []))
        if isinstance(bpy.context.scene.get("warnings", []), list)
        else [],
    }
    report["duration_seconds"] = round(time.time() - started, 3)

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(f"REPORT={output_path}")
    print(
        f"OBJECTS={len(bpy.data.objects)} MESHES={len(mesh_records)} "
        f"VERTICES={total_vertices} TRIANGLES={total_triangles} "
        f"MATERIALS={len(material_records)} IMAGES={len(image_records)}"
    )


if __name__ == "__main__":
    main()
