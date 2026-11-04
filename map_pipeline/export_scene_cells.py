#!/usr/bin/env python3
"""Export Blender scene cells as Source 2 ModelDoc assets and map manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Matrix

# Blender's --python entry point omits the script directory from sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_df_glass import glass_material
from spaceport_collision_rules import COLLISION_NAME_RE


SHADER = "csgo_complex.vfx"
MATERIAL_PREFIX = "materials/df_full_v2/m"
TEXTURE_PREFIX = "materials/df_full_v2/t"
IMAGE_EXTENSIONS = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "OPEN_EXR": ".exr",
    "HDR": ".hdr",
    "TARGA": ".tga",
    "TARGA_RAW": ".tga",
    "TIFF": ".tif",
}



def digest(text: str, length: int = 12) -> str:
    return hashlib.blake2b(text.encode("utf-8"), digest_size=8).hexdigest()[:length]


def safe_stem(text: str, limit: int = 32) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._")
    return (value or "asset")[:limit]


def source_path(root: Path, relative: str) -> Path:
    return root.joinpath(*relative.replace("\\", "/").split("/"))


def material_path(material_name: str) -> str:
    return f"{MATERIAL_PREFIX}/{digest(material_name)}.vmat"


def image_path(image: bpy.types.Image) -> tuple[str, Path, str]:
    extension = IMAGE_EXTENSIONS.get(image.file_format, ".png")
    relative = (
        f"{TEXTURE_PREFIX}/{safe_stem(image.name)}_{digest(image.name)}{extension}"
    )
    return relative, extension, safe_stem(image.name)


def input_socket(node: bpy.types.Node, names: tuple[str, ...]):
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            return socket
    return None


def connected_images(socket) -> list[bpy.types.Image]:
    if socket is None or not socket.is_linked:
        return []
    images = []
    visited = set()
    stack = [link.from_node for link in socket.links]
    while stack:
        node = stack.pop()
        if node.as_pointer() in visited:
            continue
        visited.add(node.as_pointer())
        if node.type == "TEX_IMAGE" and node.image is not None:
            images.append(node.image)
            continue
        for child in node.inputs:
            for link in child.links:
                stack.append(link.from_node)
    return images


def image_score(image: bpy.types.Image, role: str) -> tuple[int, int]:
    name = image.name.lower()
    score = 0
    if role == "color":
        for index, token in enumerate(
            ("_cc_hd", "_c_hd", "_ca_hd", "_color", "_basecolor", "_d", "_ch_hd")
        ):
            if token in name:
                score = max(score, 100 - index)
        if any(token in name for token in ("black", "normal", "_n_", "_nr_", "_mra_", "_mac_")):
            score -= 80
    elif role == "normal":
        for index, token in enumerate(("_n_hd", "_nr_hd", "_nrm", "_normal", "_n_")):
            if token in name:
                score = max(score, 100 - index)
        if "default_standardnormal" in name:
            score -= 20
    elif role in {"roughness", "metalness", "occlusion"}:
        for index, token in enumerate(("_mra_hd", "_mac_hd", "_orm_", "_rm_", "_ch_hd")):
            if token in name:
                score = max(score, 100 - index)
    elif role == "emission":
        for index, token in enumerate(("_ec_hd", "_emissive", "_e_hd")):
            if token in name:
                score = max(score, 100 - index)
    return score, image.size[0] * image.size[1]


def best_image(
    images: list[bpy.types.Image],
    role: str,
    require_matching_name: bool,
):
    candidates = []
    for image in images:
        if role in {"roughness", "metalness", "occlusion"} and image.file_format in {
            "HDR",
            "OPEN_EXR",
        }:
            continue
        score, area = image_score(image, role)
        if require_matching_name and score <= 0:
            continue
        candidates.append((score, area, image))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def srgb_value(value) -> str:
    if hasattr(value, "__len__") and len(value) >= 3:
        components = [float(value[index]) for index in range(min(4, len(value)))]
        if len(components) == 3:
            components.append(1.0)
    else:
        components = [float(value), float(value), float(value), 1.0]
    return "[{}]".format(" ".join(f"{component:.6f}" for component in components))


def export_image(
    image: bpy.types.Image,
    content_root: Path,
    exported_images: dict[str, str],
) -> str | None:
    key = image.name
    if key in exported_images and exported_images[key]:
        return exported_images[key]

    relative, extension, _ = image_path(image)
    destination = source_path(content_root, relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not destination.exists():
            packed = image.packed_file
            if packed is not None and hasattr(packed, "data"):
                destination.write_bytes(bytes(packed.data))
            else:
                previous_format = image.file_format
                image.file_format = (
                    "PNG" if extension in {".jpg", ".png"} else previous_format
                )
                image.save_render(str(destination), scene=bpy.context.scene)
                image.file_format = previous_format
        exported_images[key] = relative
        return relative
    except Exception as error:
        print(f"IMAGE_EXPORT_FAILED name={image.name!r} error={error}")
        exported_images[key] = ""
        return None


def material_image_roles(material: bpy.types.Material):
    if not material.use_nodes or not material.node_tree:
        return {}, []
    principled = next(
        (node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
        None,
    )
    if principled is None:
        return {}, []

    sockets = {
        "color": input_socket(principled, ("Base Color",)),
        "normal": input_socket(principled, ("Normal",)),
        "roughness": input_socket(principled, ("Roughness",)),
        "metalness": input_socket(principled, ("Metallic",)),
        "emission": input_socket(
            principled, ("Emission Color", "Emission")
        ),
        "alpha": input_socket(principled, ("Alpha",)),
    }
    all_images = []
    role_images = {}
    for role, socket in sockets.items():
        images = connected_images(socket)
        all_images.extend(images)
        role_images[role] = best_image(
            images, role, require_matching_name=False
        )

    node_images = [
        node.image
        for node in material.node_tree.nodes
        if node.type == "TEX_IMAGE" and node.image is not None
    ]
    for role in ("color", "normal", "roughness", "metalness", "emission"):
        if role_images.get(role) is None:
            role_images[role] = best_image(
                node_images,
                role,
                require_matching_name=role != "color",
            )
    if role_images.get("roughness") is None:
        role_images["roughness"] = role_images.get("metalness")
    if role_images.get("metalness") is None:
        role_images["metalness"] = role_images.get("roughness")
    role_images["occlusion"] = role_images.get("roughness")
    return role_images, list(dict.fromkeys(all_images + node_images))


def write_material(
    material: bpy.types.Material,
    source_name: str,
    content_root: Path,
    exported_images: dict[str, str],
) -> dict:
    relative = material_path(source_name)
    destination = source_path(content_root, relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    roles, images = material_image_roles(material)
    image_paths = {
        image.name: export_image(image, content_root, exported_images)
        for image in images
    }
    manifest = {
        "source_name": source_name,
        "vmat": relative,
        "images": image_paths,
        "roles": {role: image.name if image else None for role, image in roles.items()},
    }
    glass = glass_material(source_name, image_paths, manifest["roles"])
    if glass is not None:
        destination.write_text(glass, encoding="utf-8")
        return manifest

    principled = None
    if material.use_nodes and material.node_tree:
        principled = next(
            (
                node
                for node in material.node_tree.nodes
                if node.type == "BSDF_PRINCIPLED"
            ),
            None,
        )

    base_color = (0.8, 0.8, 0.8, 1.0)
    roughness = (0.5, 0.5, 0.5, 0.5)
    metalness = (0.0, 0.0, 0.0, 0.0)
    emission = (0.0, 0.0, 0.0, 1.0)
    alpha = 1.0
    if principled is not None:
        base_socket = principled.inputs.get("Base Color")
        roughness_socket = principled.inputs.get("Roughness")
        metalness_socket = principled.inputs.get("Metallic")
        emission_socket = input_socket(principled, ("Emission Color", "Emission"))
        emission_strength_socket = principled.inputs.get("Emission Strength")
        alpha_socket = principled.inputs.get("Alpha")
        if base_socket is not None:
            base_color = tuple(base_socket.default_value)
        if roughness_socket is not None:
            roughness = (float(roughness_socket.default_value),) * 4
        if metalness_socket is not None:
            metalness = (float(metalness_socket.default_value),) * 4
        if emission_socket is not None:
            emission = tuple(emission_socket.default_value)
            emission_strength = (
                1.0
                if emission_socket.is_linked
                else float(emission_strength_socket.default_value)
                if emission_strength_socket is not None
                else 1.0
            )
            emission = tuple(float(value) * emission_strength for value in emission)
        if alpha_socket is not None:
            alpha = float(alpha_socket.default_value)
    else:
        base_color = tuple(material.diffuse_color)
        roughness = (float(getattr(material, "roughness", 0.5)),) * 4
        metalness = (float(getattr(material, "metallic", 0.0)),) * 4

    lines = [
        "Layer0",
        "{",
        f'\tshader "{SHADER}"',
        "",
        "\tF_PAINT_VERTEX_COLORS 0",
        "\tF_ADDITIVE_BLEND 0",
        "\tF_ALPHA_TEST 0",
        '\tg_bFogEnabled "1"',
        "",
    ]

    if source_name.startswith("MI_H_Building_FutureTech_HLight_01_ExterWall_01_01"):
        lines.append("\tF_RENDER_BACKFACES 1")

    for role, property_name in (
        ("color", "TextureColor"),
        ("normal", "TextureNormal"),
        ("roughness", "TextureRoughness"),
        ("metalness", "TextureMetalness"),
        ("occlusion", "TextureAmbientOcclusion"),
    ):
        image = roles.get(role)
        path = image_paths.get(image.name, "") if image else ""
        if path:
            lines.append(f'\t{property_name} "{path}"')
        elif role == "color":
            lines.append(f'\t{property_name} "{srgb_value(base_color)}"')
        elif role == "roughness":
            lines.append(f'\t{property_name} "{srgb_value(roughness)}"')
        elif role == "metalness":
            lines.append(f'\t{property_name} "{srgb_value(metalness)}"')

    emission_image = roles.get("emission")
    emission_path = (
        image_paths.get(emission_image.name, "") if emission_image else ""
    )
    if emission_path:
        lines.append(f'\tTextureSelfIllumMask "{emission_path}"')
        lines.append('\tg_vSelfIllumTint "[1.000000 1.000000 1.000000]"')
    elif max(float(value) for value in emission[:3]) > 0.001:
        lines.append(f'\tg_vEmissiveColor "{srgb_value(emission)}"')

    blended = alpha < 0.999
    if hasattr(material, "surface_render_method"):
        blended = blended or "DITHER" in str(material.surface_render_method).upper()
    # These opaque materials store non-opacity masks in base color alpha.
    if source_name in {
        "MI_C_RoadFacility_Collapse_Bridge_Pipeline_01B_HD",
        "MI_FutureTech_Mechanical_Dynamo_01B_HD",
        "MI_GEN_Marble_Checkered_38_HD",
        "MI_GEN_Marble_Checkred_04",
        "MI_GEN_Metal_Base_01B_HD",
        "MI_GEN_Metal_Base_01C_HD",
        "MI_GEN_Metal_Base_01_HD",
        "MI_GEN_Metal_Base_02_HD",
        "MI_GEN_Metal_PaintingFloor_03_HD",
        "MI_H_Brakkesh_BigDoor_02c_HD",
        "MI_H_Building_FutureTech_Aerospace_02_03_HD",
        "MI_H_Building_FutureTech_Ground_23_HD",
        "MI_H_Building_FutureTech_HLight_01_ExterWall_01_01A_HD",
        "MI_H_Building_FutureTech_HLight_01_ExterWall_01_01B_HD",
        "MI_H_Building_FutureTech_HLight_01_ExterWall_01_01D_HD",
        "MI_H_Building_FutureTech_HLight_01_ExterWall_Damage_01B_01E_HD",
        "MI_H_Building_FutureTech_HLight_01_ExterWall_Damage_02_01_HD",
        "MI_H_Building_FutureTech_HLight_01_InterWall_04G_HD",
        "MI_H_Building_FutureTech_HOrange_01_ExterWall_01_01A_HD",
        "MI_H_Building_FutureTech_HOrange_01_InterWall_01C_HD",
        "MI_H_Building_FutureTech_Metalwall_02_HD",
        "MI_H_Building_Militarily_NavalBattle_S6_Ground_05a_HD",
        "MI_H_Building_Tide_Ground_Metal_04_HD",
        "MI_H_FutureTech_Electrical_BigConditioners_01B_HD",
        "MI_H_FutureTech_Furniture_Cabinet_10A_HD",
        "MI_H_FutureTech_Furniture_Cabinet_10_HD",
        "MI_H_FutureTech_Furniture_Cabinet_15A_HD",
        "MI_H_FutureTech_Furniture_Cabinet_15B_HD",
        "MI_H_FutureTech_Furniture_Cabinet_15_HD",
        "MI_H_FutureTech_Furniture_Cabinet_16_HD",
        "MI_H_FutureTech_Furniture_FoodCans_02_HD",
        "MI_H_FutureTech_Furniture_Speakers_01_A_HD",
        "MI_H_FutureTech_Furniture_Table_02_HD",
        "MI_H_FutureTech_Furniture_ToolTable_01_HD",
        "MI_H_FutureTech_Furniture_Utility_Dustbin_01_HD",
        "MI_H_FutureTech_Furniture_Utility_Dustbin_02_HD",
        "MI_H_FutureTech_Machinery_Cabinet_01_HD",
        "MI_H_FutureTech_Machinery_Cabinet_02_HD",
        "MI_H_FutureTech_Resort_Flowerpot_05_HD",
        "MI_H_FutureTech_Robotic_Path_01_HD",
        "MI_H_FutureTech_Tools_Box_03A_HD",
        "MI_H_FutureTech_Tools_Box_03_HD",
        "MI_H_GEN_Building_CeilingConcrete_01a",
        "MI_H_Government_Office_Statue_01A_HD",
        "MI_H_Government_Office_Statue_02A_HD",
        "MI_H_Government_Office_Table_02A_HD",
        "MI_H_Government_Office_Table_03B_HD",
        "MI_H_Government_Office_Table_04B_HD",
        "MI_H_Industrial_Container_SupplyBox_02A_Black_HD",
        "MI_H_Industrial_Container_SupplyBox_02A_HD",
        "MI_H_Industrial_ISS_Centrifuge_04_HD",
        "MI_H_Industrial_ISS_Centrifuge_05_HD",
        "MI_H_Industrial_ISS_Centrifuge_06_HD",
        "MI_H_Industrial_Tools_OxygenCylinder_01A_HD",
        "MI_H_Residential_Bedroom_Cabinet_01B_HD",
        "MI_H_Residential_Bedroom_Cabinet_02B_HD",
        "MI_H_Residential_Bedroom_Cabinet_03B_HD",
        "MI_H_Residential_Bedroom_Cabinet_03C_HD",
        "MI_H_Residential_Bedroom_Cupboard_01B_HD",
        "MI_H_Residential_Bedroom_Cupboard_01C_HD",
        "MI_H_Residential_Bedroom_Shelf_01C_HD",
        "MI_H_Residential_Bedroom_Table_01_HD",
        "MI_H_Small_Door_11_HD",
        "MI_H_Transport_Utility_Escalator_01B_HD",
        "MI_H_Update_Container_PlasticBox_02A_HD",
        "MI_H_Update_Container_PlasticBox_02B_HD",
        "MI_I_RoadFacility_Ground_C_04b_HD",
        "MI_I_RoadFacility_Ground_L_10_03_HD",
        "MI_I_RoadFacility_Ground_L_10_Ruin_10_HD",
        "MI_I_WalkwaySystem_MetalFloor_01F_HD",
        "MI_I_WalkwaySystem_MetalFloor_01_C_HD",
        "MI_Industrial_Electrical_Lift_01C_HD",
        "MI_M_Commercial_Resort_Sofa_11B_HD",
        "MI_M_Commercial_Sanitary_HandDryer_01_HD",
        "MI_M_Government_Office_FoldingTable_01_HD",
        "MI_M_Government_Office_ProjectorScreen_01A_HD",
        "MI_M_Government_Office_ProjectorScreen_01_HD",
        "MI_M_Government_Office_Storagebox_01_HD",
        "MI_M_Government_Office_TableMoveable_02A_HD",
        "MI_M_Government_Office_WoodenCabinet_01B_HD",
        "MI_M_Government_Office_WoodenCabinet_01C_HD",
    }:
        blended = False
    if blended:
        lines.append("\tF_ALPHA_TEST 1")
        lines.append('\tg_flAlphaTestReference "0.500000"')

    lines.extend(["}", ""])
    destination.write_text("\n".join(lines), encoding="utf-8")
    return manifest


def write_vmdl(
    cell_root: Path, cell_name: str, model_prefix: str
) -> str:
    relative = f"{model_prefix}/{cell_name}.vmdl"
    destination = cell_root.joinpath(f"{cell_name}.vmdl")
    destination.write_text(
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
                '\t\t\t\t\t\tname = ""',
                f'\t\t\t\t\t\tfilename = "{model_prefix}/{cell_name}.fbx"',
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
                "\t\t\t\tchildren =",
                "\t\t\t\t[",
                "\t\t\t\t\t{",
                '\t\t\t\t\t\t_class = "PhysicsMeshFromRender"',
                '\t\t\t\t\t\tparent_bone = ""',
                '\t\t\t\t\t\tsurface_prop = "default"',
                '\t\t\t\t\t\tcollision_prop = "default"',
                '\t\t\t\t\t\ttool_material = ""',
                "\t\t\t\t\t\trenderMeshList = [  ]",
                "\t\t\t\t\t},",
                "\t\t\t\t]",
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
    return relative


def object_center(record: dict) -> tuple[float, float, float]:
    bounds = record["bounds"]
    return tuple(
        (bounds["min"][axis] + bounds["max"][axis]) * 0.5 for axis in range(3)
    )


def export_cell(
    grid: tuple[int, int],
    records: list[dict],
    content_root: Path,
    cell_size: float,
    source_center: tuple[float, float, float],
    target_center: tuple[float, float, float],
    exported_images: dict[str, str],
    material_library: dict[str, dict],
    model_prefix: str,
    decimate_ratio: float,
) -> dict:
    cell_name = f"cell_{grid[0]}_{grid[1]}"
    cell_root = content_root / Path(model_prefix)
    cell_root.mkdir(parents=True, exist_ok=True)
    fbx_destination = cell_root.joinpath(f"{cell_name}.fbx")
    objects = [bpy.data.objects.get(record["name"]) for record in records]
    objects = [
        obj
        for obj in objects
        if obj is not None and obj.type == "MESH" and obj.data is not None
    ]
    if not objects:
        raise RuntimeError(f"no exportable mesh objects for {cell_name}")

    used_materials = []
    for obj in objects:
        for slot in obj.material_slots:
            if slot.material is not None and slot.material not in used_materials:
                used_materials.append(slot.material)

    material_records = []
    for material in used_materials:
        original_name = material.get("df_source_material_name", material.name)
        if original_name not in material_library:
            material_library[original_name] = write_material(
                material, original_name, content_root, exported_images
            )
        material_records.append(original_name)
    if not used_materials:
        raise RuntimeError(f"no materials found for {cell_name}")

    cell_origin = (grid[0] * cell_size, grid[1] * cell_size, 0.0)
    original_matrices = {obj.name: obj.matrix_world.copy() for obj in objects}
    compensation = Matrix.Rotation(math.radians(-90.0), 4, "Z")
    for obj in objects:
        matrix = obj.matrix_world.copy()
        matrix.translation.x -= cell_origin[0]
        matrix.translation.y -= cell_origin[1]
        matrix.translation.z -= cell_origin[2]
        obj.matrix_world = compensation @ matrix

    bpy.ops.object.select_all(action="DESELECT")
    added_modifiers = []
    if 0.0 < decimate_ratio < 1.0:
        for obj in objects:
            modifier = obj.modifiers.new("DF_CollisionDecimate", "DECIMATE")
            modifier.ratio = decimate_ratio
            modifier.use_collapse_triangulate = True
            added_modifiers.append((obj, modifier))
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.context.view_layer.update()
    bpy.ops.export_scene.fbx(
        filepath=str(fbx_destination),
        use_selection=True,
        object_types={"MESH"},
        apply_scale_options="FBX_SCALE_ALL",
        mesh_smooth_type="FACE",
        use_mesh_modifiers=True,
        bake_anim=False,
        add_leaf_bones=False,
        path_mode="AUTO",
    )
    for obj, modifier in added_modifiers:
        obj.modifiers.remove(modifier)

    for obj in objects:
        obj.matrix_world = original_matrices[obj.name]
    bpy.context.view_layer.update()

    vmdl_relative = write_vmdl(cell_root, cell_name, model_prefix)
    map_position = (
        target_center[0] - source_center[0] + cell_origin[0],
        target_center[1] - source_center[1] + cell_origin[1],
        target_center[2] - source_center[2] + cell_origin[2],
    )
    return {
        "name": cell_name,
        "grid": list(grid),
        "cell_size": cell_size,
        "cell_origin_blender": list(cell_origin),
        "map_origin": list(map_position),
        "objects": len(objects),
        "triangles": sum(record["mesh"]["triangles"] for record in records),
        "vertices": sum(record["mesh"]["vertices"] for record in records),
        "fbx": f"{model_prefix}/{cell_name}.fbx",
        "vmdl": vmdl_relative,
        "material_sources": sorted(material_records),
        "object_names": [record["name"] for record in records],
    }


def main() -> None:
    started = time.time()
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--content-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--cell-size", type=float, default=10.0)
    parser.add_argument("--cell", action="append", default=[])
    parser.add_argument("--max-cells", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--source-center", default="6693.91505,4578.046,-220.48575")
    parser.add_argument("--target-center", default="512,160,0")
    parser.add_argument("--model-prefix", default="models/df_full/c")
    parser.add_argument("--collision-only", action="store_true")
    parser.add_argument("--decimate-ratio", type=float, default=1.0)
    parsed = parser.parse_args(args)

    inventory_path = Path(parsed.inventory).resolve()
    content_root = Path(parsed.content_root).resolve()
    manifest_path = Path(parsed.manifest).resolve()
    with inventory_path.open("r", encoding="utf-8") as handle:
        inventory = json.load(handle)
    source_center = tuple(float(value) for value in parsed.source_center.split(","))
    target_center = tuple(float(value) for value in parsed.target_center.split(","))

    for material in bpy.data.materials:
        source_name = material.get("df_source_material_name", material.name)
        material["df_source_material_name"] = source_name
        material.name = material_path(source_name)[:-5]

    records_by_cell = defaultdict(list)
    for record in inventory["objects"]:
        if record["type"] != "MESH" or not record.get("bounds"):
            continue
        if parsed.collision_only and not COLLISION_NAME_RE.search(record["name"]):
            continue
        center = object_center(record)
        grid = (
            math.floor(center[0] / parsed.cell_size),
            math.floor(center[1] / parsed.cell_size),
        )
        records_by_cell[grid].append(record)

    requested = []
    for value in parsed.cell:
        x, y = (int(part) for part in value.split(","))
        requested.append((x, y))
    if requested:
        cells = [(grid, records_by_cell[grid]) for grid in requested]
    else:
        cells = sorted(
            records_by_cell.items(),
            key=lambda item: (
                -sum(record["mesh"]["triangles"] for record in item[1]),
                item[0],
            ),
        )
    if parsed.max_cells > 0:
        cells = cells[: parsed.max_cells]

    exported_images: dict[str, str] = {}
    material_library: dict[str, dict] = {}
    exported_cells = []
    existing_by_name = {}
    if parsed.resume and manifest_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        material_library.update(existing_manifest.get("materials", {}))
        for cell in existing_manifest.get("cells", []):
            fbx_exists = source_path(content_root, cell["fbx"]).exists()
            vmdl_exists = source_path(content_root, cell["vmdl"]).exists()
            if fbx_exists and vmdl_exists:
                existing_by_name[cell["name"]] = cell
        exported_cells.extend(existing_by_name.values())

    pending_cells = [
        (grid, records)
        for grid, records in cells
        if not (parsed.resume and f"cell_{grid[0]}_{grid[1]}" in existing_by_name)
    ]
    if parsed.max_cells > 0:
        pending_cells = pending_cells[: parsed.max_cells]

    manifest = {
        "source_blend": bpy.data.filepath,
        "duration_seconds": None,
        "cell_size": parsed.cell_size,
        "source_center": list(source_center),
        "target_center": list(target_center),
        "material_prefix": MATERIAL_PREFIX,
        "texture_prefix": TEXTURE_PREFIX,
        "model_prefix": parsed.model_prefix,
        "collision_only": parsed.collision_only,
        "decimate_ratio": parsed.decimate_ratio,
        "materials": material_library,
        "cells": exported_cells,
    }
    for index, (grid, records) in enumerate(pending_cells, start=1):
        print(
            f"EXPORT_CELL {index}/{len(pending_cells)} grid={grid} "
            f"objects={len(records)}"
        )
        cell = export_cell(
            grid,
            records,
            content_root,
            parsed.cell_size,
            source_center,
            target_center,
            exported_images,
            material_library,
            parsed.model_prefix,
            parsed.decimate_ratio,
        )
        exported_cells = [
            existing
            for existing in exported_cells
            if existing["name"] != cell["name"]
        ]
        exported_cells.append(cell)
        manifest["duration_seconds"] = round(time.time() - started, 3)
        manifest["materials"] = material_library
        manifest["cells"] = sorted(
            exported_cells, key=lambda item: tuple(item["grid"])
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    manifest["materials"] = material_library
    manifest["cells"] = sorted(exported_cells, key=lambda item: tuple(item["grid"]))
    manifest["duration_seconds"] = round(time.time() - started, 3)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"MANIFEST={manifest_path} CELLS={len(exported_cells)} "
        f"IMAGES={len([value for value in exported_images.values() if value])}"
    )


if __name__ == "__main__":
    main()
