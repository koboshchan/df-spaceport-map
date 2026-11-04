#!/usr/bin/env python3
"""Export FBX axis calibration boxes for the Source 2 ModelDoc compiler."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import bpy


def write_vmdl(path: Path, name: str) -> None:
    path.write_text(
        "\n".join(
            [
                "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc36:version{972dada4-b828-45a4-bb93-7795cf0585da} -->",
                "{",
                "\trootNode =",
                "\t{",
                '\t\t_class = "RootNode"',
                "\t\tchildren =",
                "\t\t[",
                "\t\t\t{",
                '\t\t\t\t_class = "RenderMeshList"',
                "\t\t\t\tchildren =",
                "\t\t\t\t[",
                "\t\t\t\t\t{",
                '\t\t\t\t\t\t_class = "RenderMeshFile"',
                f'\t\t\t\t\t\tname = "{name}"',
                f'\t\t\t\t\t\tfilename = "models/df_full/probes/{name}.fbx"',
                "\t\t\t\t\t\timport_scale = 1.0",
                "\t\t\t\t\t\timport_filter =",
                "\t\t\t\t\t\t{",
                "\t\t\t\t\t\t\texclude_by_default = false",
                "\t\t\t\t\t\t\texception_list = [  ]",
                "\t\t\t\t\t\t}",
                "\t\t\t\t\t},",
                "\t\t\t\t]",
                "\t\t\t},",
                "\t\t\t{",
                '\t\t\t\t_class = "PhysicsShapeList"',
                "\t\t\t\tchildren = [  ]",
                "\t\t\t\tleave_body_collision_unmodified = false",
                "\t\t\t},",
                "\t\t]",
                '\t\tmodel_archetype = ""',
                '\t\tprimary_associated_entity = ""',
                '\t\tanim_graph_name = ""',
                '\t\tdocument_sub_type = "ModelDocSubType_None"',
                "\t}",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) != 2:
        raise SystemExit("usage: export_axis_probes.py -- <content addon> <output fbx dir>")
    content_root = Path(args[0]).resolve()
    output_root = Path(args[1]).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    model_root = content_root / "models" / "df_full" / "probes"
    model_root.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=1)
    cube = bpy.context.object
    cube.name = "axis_probe"
    cube.scale = (10, 20, 30)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    material = bpy.data.materials.new("materials/df_full/m/0deacc95684c")
    cube.data.materials.append(material)

    variants = [
        ("probe_default", {}),
        ("probe_yz", {"axis_forward": "Y", "axis_up": "Z"}),
        ("probe_nyz", {"axis_forward": "-Y", "axis_up": "Z"}),
        ("probe_offset", {}),
    ]
    for name, options in variants:
        cube.location = (1.0, 2.0, 3.0) if name == "probe_offset" else (0.0, 0.0, 0.0)
        fbx_path = output_root / f"{name}.fbx"
        bpy.ops.export_scene.fbx(
            filepath=str(fbx_path),
            use_selection=True,
            object_types={"MESH"},
            apply_scale_options="FBX_SCALE_ALL",
            mesh_smooth_type="FACE",
            bake_anim=False,
            **options,
        )
        write_vmdl(model_root / f"{name}.vmdl", name)
        print(f"EXPORTED={fbx_path}")


if __name__ == "__main__":
    main()
