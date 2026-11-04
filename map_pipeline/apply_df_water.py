#!/usr/bin/env python3
"""Replace imported Spaceport water materials with the CS2 water shader."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


WATER_FOG_COLORS = {
    "MI_WaterHD_SpaceCenter": "0.030000 0.145000 0.155000 0.000000",
    "MI_WaterHD_FutureTech_01": "0.025000 0.185000 0.225000 0.000000",
    "MI_WaterHD_SpaceCenter_Oil_1": "0.025000 0.085000 0.070000 0.000000",
    "MI_WaterHD_SpaceCenter_Oil_2": "0.030000 0.075000 0.055000 0.000000",
    "MI_WaterHD_SpaceCenter_Oil_3": "0.035000 0.070000 0.045000 0.000000",
}

WATER_NORMAL = "materials/dev/water_normal_mks_558bf690.vtex_c"


def water_material(normal_path: str, fog_color: str) -> str:
    return f"""Layer0
{{
    shader "csgo_water.vfx"

    F_ANIMATED_NORMALS 1
    F_FRESNEL 1

    g_flReflectionAmount "0.900000"
    g_flRefractionAmount "1.000000"
    g_flWaterDepth "400.000000"
    g_flWaterStart "1.000000"
    g_vWaterFogColor "[{fog_color}]"
    g_tNormal "{normal_path}"

    mapbuilder.nonsolid 1
    mapbuilder.water 1
    PhysicsSurfaceProperties "water"
}}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--addon-root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--content-root", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    addon_root = args.addon_root.resolve()
    backup_root = args.backup_root.resolve()
    content_root = args.content_root.resolve() if args.content_root else None
    modified = []

    for source_name, fog_color in WATER_FOG_COLORS.items():
        record = manifest["materials"].get(source_name)
        if record is None:
            raise RuntimeError(f"Water material is missing from manifest: {source_name}")

        relative = Path(record["vmat"].replace("\\", "/"))
        source = addon_root.joinpath(*relative.parts)
        if not source.is_file():
            raise FileNotFoundError(source)

        backup = backup_root.joinpath(*relative.parts)
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(source, backup)

        normal_source = record["roles"].get("normal")
        if not normal_source:
            raise RuntimeError(f"No source normal texture recorded for {source_name}")
        normal_path = WATER_NORMAL
        source.write_text(
            water_material(normal_path, fog_color),
            encoding="utf-8",
        )

        if content_root is not None:
            destination = content_root.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        modified.append(
            {
                "source_name": source_name,
                "vmat": str(relative).replace("\\", "/"),
                "normal": normal_path,
                "source_normal": record["images"][normal_source],
                "fog_color": fog_color,
            }
        )

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(
            {
                "shader": "csgo_water.vfx",
                "modified": modified,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"WATER_MATERIALS={len(modified)} "
        f"ADDON_ROOT={addon_root} "
        f"REPORT={args.report}"
    )


if __name__ == "__main__":
    main()
