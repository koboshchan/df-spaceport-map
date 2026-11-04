import sys

import bpy


args = sys.argv[sys.argv.index("--") + 1 :]
if len(args) != 1:
    raise SystemExit("usage: export_test_model.py -- <output.fbx>")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=64)
cube = bpy.context.object
cube.name = "spaceport_test_cube"

material = bpy.data.materials.new(
    "models/df_spaceport_full/spaceport_test_material"
)
material.diffuse_color = (0.08, 0.22, 0.32, 1.0)
cube.data.materials.append(material)

bpy.ops.export_scene.fbx(
    filepath=args[0],
    use_selection=True,
    apply_scale_options="FBX_SCALE_ALL",
    object_types={"MESH"},
    mesh_smooth_type="FACE",
)
print(f"EXPORTED={args[0]}")
