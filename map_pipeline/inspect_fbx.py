#!/usr/bin/env python3
"""Import FBX files and print their root mesh structure."""

from __future__ import annotations

import os
import sys

import bpy


def main() -> None:
    paths = sys.argv[sys.argv.index("--") + 1 :]
    if not paths:
        raise SystemExit("usage: inspect_fbx.py -- <file.fbx> [...]")

    for path in paths:
        absolute = os.path.abspath(path)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        try:
            result = bpy.ops.import_scene.fbx(filepath=absolute)
        except Exception as error:
            print(f"FBX={absolute} IMPORT_FAILED={error}")
            continue
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        print(
            f"FBX={absolute} RESULT={result} OBJECTS={len(bpy.context.scene.objects)} "
            f"MESHES={len(meshes)}"
        )
        for obj in meshes[:40]:
            materials = [
                slot.material.name if slot.material else None
                for slot in obj.material_slots
            ]
            print(
                f"  OBJ name={obj.name!r} data={obj.data.name!r} "
                f"verts={len(obj.data.vertices)} polys={len(obj.data.polygons)} "
                f"materials={materials} loc={tuple(round(v, 3) for v in obj.location)}"
            )


if __name__ == "__main__":
    main()
