"""Build a VMap variant backed by collision models with no render geometry."""

import argparse
import re
from pathlib import Path

MODEL_PATH = re.compile(r'(?<="model" "string" ")models/df_collision80/c/(cell_-?\d+_-?\d+)\.vmdl')
RENDER_MESH = re.compile(r'(?ms)^\t{3}\{\n\t{4}_class = "RenderMeshList".*?^\t{3}\},\n')


def physics_only_model(model, mesh_path):
    model, removed = RENDER_MESH.subn("", model)
    if removed != 1 or model.count('"PhysicsMeshFromRender"') != 1 or model.count("renderMeshList = [  ]") != 1:
        raise ValueError(f"Unexpected collision model schema for {mesh_path}")
    return model.replace('"PhysicsMeshFromRender"', '"PhysicsMeshFile"').replace(
        "renderMeshList = [  ]",
        f'filename = "{mesh_path}"\n\t\t\t\t\t\timport_scale = 1.0',
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_map", type=Path)
    parser.add_argument("content_addon", type=Path)
    parser.add_argument("model_output", type=Path)
    parser.add_argument("output_map", type=Path)
    args = parser.parse_args()
    vmap = args.source_map.read_text(encoding="utf-8-sig")
    cells = sorted(set(MODEL_PATH.findall(vmap)))
    if not cells:
        parser.error("source map does not contain collision cells")

    args.model_output.mkdir(parents=True, exist_ok=True)
    for cell in cells:
        model_path = f"models/df_collision80/c/{cell}"
        model = (args.content_addon / f"{model_path}.vmdl").read_text(encoding="utf-8-sig")
        (args.model_output / f"{cell}.vmdl").write_text(
            physics_only_model(model, f"{model_path}.fbx"), encoding="utf-8"
        )

    vmap = MODEL_PATH.sub(r"models/df_collision80/physics/\1.vmdl", vmap)
    args.output_map.write_text(vmap, encoding="utf-8")
    print(f"Generated {len(cells)} collision-only models")


if __name__ == "__main__":
    main()
