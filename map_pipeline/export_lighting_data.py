#!/usr/bin/env python3
"""Export Blender lights and world lighting metadata for Source 2 mapping."""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def srgb_channel(value: float) -> float:
    value = max(0.0, min(1.0, float(value)))
    if value <= 0.0031308:
        return value * 12.92
    return 1.055 * (value ** (1.0 / 2.4)) - 0.055


def color_bytes(color) -> list[int]:
    return [round(srgb_channel(value) * 255.0) for value in color[:3]]


def source_angles(direction: Vector) -> list[float]:
    direction = direction.normalized()
    yaw = math.degrees(math.atan2(direction.y, direction.x))
    pitch = -math.degrees(math.asin(max(-1.0, min(1.0, direction.z))))
    return [pitch, yaw, 0.0]


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) != 1:
        raise SystemExit("usage: export_lighting_data.py -- <output.json>")
    output_path = Path(args[0]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for light_object in bpy.data.objects:
        if light_object.type != "LIGHT":
            continue
        light = light_object.data
        matrix = light_object.matrix_world
        local_direction = matrix.to_quaternion() @ Vector((0.0, 0.0, -1.0))
        if light.type == "SUN":
            direction = local_direction.normalized()
        else:
            direction = local_direction.normalized()
        cutoff_distance = float(getattr(light, "cutoff_distance", 0.0) or 0.0)
        record = {
            "name": light_object.name,
            "type": light.type,
            "location": [round(value, 6) for value in matrix.translation],
            "direction": [round(value, 8) for value in direction],
            "angles": [round(value, 6) for value in source_angles(direction)],
            "energy": float(light.energy),
            "color": color_bytes(light.color),
            "linear_color": [float(value) for value in light.color],
            "use_shadow": bool(light.use_shadow),
            "cutoff_distance": cutoff_distance,
            "visible_camera": bool(getattr(light, "visible_camera", True)),
            "hide_render": bool(light_object.hide_render),
        }
        if light.type == "SPOT":
            outer_cone = math.degrees(float(light.spot_size))
            inner_cone = outer_cone * (1.0 - float(light.spot_blend))
            record["outercone"] = round(outer_cone, 6)
            record["innercone"] = round(inner_cone, 6)
        elif light.type == "AREA":
            record["shape"] = light.shape
            record["size"] = float(light.size)
            record["size_y"] = float(getattr(light, "size_y", light.size))
        records.append(record)

    world_records = []
    images = {}
    for world in bpy.data.worlds:
        images_for_world = []
        nodes = []
        if world.use_nodes and world.node_tree:
            for node in world.node_tree.nodes:
                nodes.append(
                    {
                        "name": node.name,
                        "type": node.type,
                        "inputs": {
                            socket.name: list(socket.default_value)
                            if hasattr(socket.default_value, "__len__")
                            else socket.default_value
                            for socket in node.inputs
                            if hasattr(socket, "default_value")
                        },
                    }
                )
                if node.type == "TEX_IMAGE" and node.image is not None:
                    images_for_world.append(node.image.name)
                    images[node.image.name] = {
                        "filepath": bpy.path.abspath(node.image.filepath)
                        if node.image.filepath
                        else "",
                        "size": list(node.image.size),
                        "packed": bool(node.image.packed_file),
                    }
        world_records.append(
            {
                "name": world.name,
                "color": list(world.color),
                "use_nodes": world.use_nodes,
                "images": sorted(set(images_for_world)),
                "nodes": nodes,
            }
        )

    result = {
        "source_blend": bpy.data.filepath,
        "lights": records,
        "worlds": world_records,
        "world_images": images,
    }
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"LIGHT_DATA={output_path} LIGHTS={len(records)} WORLDS={len(world_records)}"
    )


if __name__ == "__main__":
    main()
