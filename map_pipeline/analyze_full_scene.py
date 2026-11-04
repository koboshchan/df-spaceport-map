#!/usr/bin/env python3
"""Summarize Source 2 import requirements for the full Blender scene."""

from __future__ import annotations

import json
import math
import os
import re
import statistics
import sys
import time
from collections import Counter, defaultdict

import bpy


def extension_group(name: str) -> str:
    stem, extension = os.path.splitext(name.lower())
    if extension:
        return extension
    return re.sub(r"\.\d+$", "", stem)[-12:]


def main() -> None:
    started = time.time()
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) != 2:
        raise SystemExit(
            "usage: analyze_full_scene.py -- <blend_inventory.json> <output.json>"
        )

    inventory_path = os.path.abspath(args[0])
    output_path = os.path.abspath(args[1])
    with open(inventory_path, "r", encoding="utf-8") as handle:
        inventory = json.load(handle)

    inventory_objects = {record["name"]: record for record in inventory["objects"]}
    mesh_data = {}
    duplicate_extra_triangles = 0
    duplicate_extra_vertices = 0
    mesh_instances = Counter()
    skinned_objects = []
    animated_objects = []
    transformed_objects = Counter()

    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.data is None:
            continue
        record = inventory_objects.get(obj.name)
        if record is None or not record.get("mesh"):
            continue
        mesh_name = obj.data.name
        mesh_instances[mesh_name] += 1
        if mesh_name not in mesh_data:
            mesh_data[mesh_name] = {
                "name": mesh_name,
                "vertices": record["mesh"]["vertices"],
                "triangles": record["mesh"]["triangles"],
                "polygons": record["mesh"]["polygons"],
                "materials": list(record["materials"]),
                "uv_layers": record["mesh"]["uv_layers"],
                "color_attributes": record["mesh"]["color_attributes"],
                "shape_keys": record["mesh"]["shape_keys"],
                "instances": 0,
            }
        else:
            duplicate_extra_triangles += record["mesh"]["triangles"]
            duplicate_extra_vertices += record["mesh"]["vertices"]
        mesh_data[mesh_name]["instances"] += 1

        if any(modifier.type == "ARMATURE" for modifier in obj.modifiers) or obj.vertex_groups:
            skinned_objects.append(obj.name)
        if obj.animation_data and obj.animation_data.action:
            animated_objects.append(obj.name)
        if any(abs(value) > 1.0e-6 for value in obj.rotation_euler):
            transformed_objects["rotated"] += 1
        if any(abs(value - 1.0) > 1.0e-6 for value in obj.scale):
            transformed_objects["scaled"] += 1
        if obj.parent is not None:
            transformed_objects["parented"] += 1

    material_nodes = Counter()
    material_records = []
    image_materials = defaultdict(set)
    for material in bpy.data.materials:
        node_types = Counter()
        images = set()
        has_principled = False
        has_output = False
        if material.use_nodes and material.node_tree:
            for node in material.node_tree.nodes:
                node_types[node.type] += 1
                material_nodes[node.type] += 1
                if node.type == "BSDF_PRINCIPLED":
                    has_principled = True
                if node.type == "OUTPUT_MATERIAL":
                    has_output = True
                if node.type == "TEX_IMAGE" and node.image:
                    images.add(node.image.name)
                    image_materials[node.image.name].add(material.name)
        material_records.append(
            {
                "name": material.name,
                "users": material.users,
                "use_nodes": material.use_nodes,
                "has_principled": has_principled,
                "has_output": has_output,
                "images": sorted(images),
                "node_types": dict(node_types),
                "surface_render_method": getattr(
                    material, "surface_render_method", None
                ),
            }
        )

    image_records = []
    image_extensions = Counter()
    for image in bpy.data.images:
        packed_size = getattr(image.packed_file, "size", 0) if image.packed_file else 0
        extension = extension_group(image.name or image.filepath)
        image_extensions[extension] += 1
        image_records.append(
            {
                "name": image.name,
                "size": list(image.size),
                "packed": bool(image.packed_file),
                "packed_size": packed_size,
                "format": image.file_format,
                "source": image.source,
                "materials": sorted(image_materials.get(image.name, set())),
            }
        )

    mesh_records = sorted(
        mesh_data.values(),
        key=lambda record: (record["triangles"] * record["instances"], record["triangles"]),
        reverse=True,
    )
    for record in mesh_records:
        record["total_triangles"] = record["triangles"] * record["instances"]

    asset_families = Counter()
    for record in mesh_records:
        name = re.sub(r"\.mo(?:\.\d+)?$", "", record["name"], flags=re.IGNORECASE)
        name = re.sub(r"\.\d{3}$", "", name)
        asset_families[name] += record["instances"]

    collection_objects = defaultdict(list)
    for record in inventory["objects"]:
        if record["type"] != "MESH" or not record.get("bounds"):
            continue
        for collection in record["collections"]:
            collection_objects[collection].append(record)
    collection_records = []
    for collection in inventory["collections"]:
        records = collection_objects[collection["name"]]
        bounds = [record["bounds"] for record in records]
        if bounds:
            minimum = [min(item["min"][i] for item in bounds) for i in range(3)]
            maximum = [max(item["max"][i] for item in bounds) for i in range(3)]
        else:
            minimum = maximum = [0.0, 0.0, 0.0]
        collection_records.append(
            {
                "name": collection["name"],
                "objects": len(records),
                "triangles": sum(item["mesh"]["triangles"] for item in records),
                "min": minimum,
                "max": maximum,
            }
        )
    collection_records.sort(key=lambda record: record["triangles"], reverse=True)

    mesh_objects = [
        record
        for record in inventory["objects"]
        if record["type"] == "MESH" and record.get("bounds")
    ]
    centers = [
        (
            (record["bounds"]["min"][0] + record["bounds"]["max"][0]) * 0.5,
            (record["bounds"]["min"][1] + record["bounds"]["max"][1]) * 0.5,
            (record["bounds"]["min"][2] + record["bounds"]["max"][2]) * 0.5,
        )
        for record in mesh_objects
    ]
    median_center = [statistics.median(center[i] for center in centers) for i in range(3)]

    def spatial_summary(cell_size):
        cells = defaultdict(
            lambda: {"objects": 0, "triangles": 0, "minimum": [math.inf] * 3, "maximum": [-math.inf] * 3}
        )
        for record in mesh_objects:
            bounds = record["bounds"]
            center = [
                (bounds["min"][i] + bounds["max"][i]) * 0.5 for i in range(3)
            ]
            key = tuple(math.floor(center[i] / cell_size) for i in range(2))
            cell = cells[key]
            cell["objects"] += 1
            cell["triangles"] += record["mesh"]["triangles"]
            for axis in range(3):
                cell["minimum"][axis] = min(cell["minimum"][axis], bounds["min"][axis])
                cell["maximum"][axis] = max(cell["maximum"][axis], bounds["max"][axis])
        output = []
        for key, cell in sorted(
            cells.items(), key=lambda item: item[1]["triangles"], reverse=True
        ):
            output.append(
                {
                    "grid": list(key),
                    "objects": cell["objects"],
                    "triangles": cell["triangles"],
                    "min": cell["minimum"],
                    "max": cell["maximum"],
                }
            )
        return output

    light_records = []
    armature_records = []
    camera_records = []
    for obj in bpy.data.objects:
        if obj.type == "LIGHT":
            light_records.append(
                {
                    "name": obj.name,
                    "type": obj.data.type,
                    "energy": obj.data.energy,
                    "color": list(obj.data.color),
                    "location": list(obj.location),
                }
            )
        elif obj.type == "ARMATURE":
            armature_records.append(
                {"name": obj.name, "bones": len(obj.data.bones)}
            )
        elif obj.type == "CAMERA":
            camera_records.append(
                {
                    "name": obj.name,
                    "type": obj.data.type,
                    "lens": obj.data.lens,
                    "location": list(obj.location),
                }
            )

    output = {
        "source_blend": bpy.data.filepath,
        "duration_seconds": None,
        "scene_bounds": inventory["scene_bounds"],
        "median_mesh_center": median_center,
        "objects": inventory["object_count"],
        "mesh_objects": inventory["mesh_object_count"],
        "unique_mesh_data": len(mesh_data),
        "duplicate_mesh_instances": sum(max(0, count - 1) for count in mesh_instances.values()),
        "duplicate_extra_triangles": duplicate_extra_triangles,
        "duplicate_extra_vertices": duplicate_extra_vertices,
        "unique_mesh_triangles": sum(record["triangles"] for record in mesh_data.values()),
        "unique_mesh_vertices": sum(record["vertices"] for record in mesh_data.values()),
        "transformed_objects": dict(transformed_objects),
        "skinned_object_count": len(skinned_objects),
        "animated_object_count": len(animated_objects),
        "skinned_objects": skinned_objects[:2000],
        "animated_objects": animated_objects[:2000],
        "mesh_data_top": mesh_records[:500],
        "asset_families_top": [
            {"name": name, "instances": count}
            for name, count in asset_families.most_common(500)
        ],
        "collections_top": collection_records[:300],
        "materials": {
            "count": len(material_records),
            "node_types": dict(material_nodes),
            "with_image": sum(bool(record["images"]) for record in material_records),
            "with_principled": sum(record["has_principled"] for record in material_records),
            "top": material_records[:1000],
        },
        "images": {
            "count": len(image_records),
            "extensions": dict(image_extensions),
            "top": sorted(
                image_records,
                key=lambda record: record["size"][0] * record["size"][1],
                reverse=True,
            )[:1000],
        },
        "lights": {
            "count": len(light_records),
            "types": dict(Counter(record["type"] for record in light_records)),
            "top": light_records[:1000],
        },
        "armatures": {
            "count": len(armature_records),
            "records": armature_records,
        },
        "cameras": camera_records,
        "spatial_50": spatial_summary(50.0)[:500],
        "spatial_100": spatial_summary(100.0)[:500],
    }
    output["duration_seconds"] = round(time.time() - started, 3)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)

    print(f"REPORT={output_path}")
    print(
        f"UNIQUE_MESHES={len(mesh_data)} "
        f"UNIQUE_TRIS={output['unique_mesh_triangles']} "
        f"DUPLICATE_EXTRA_TRIS={duplicate_extra_triangles} "
        f"SKINNED={len(skinned_objects)} "
        f"LIGHTS={len(light_records)}"
    )


if __name__ == "__main__":
    main()
