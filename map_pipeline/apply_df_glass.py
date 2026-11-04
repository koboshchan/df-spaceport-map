"""Generate Source 2 glass materials for the Spaceport model export."""

import argparse
import json
from pathlib import Path


WINDOW_PREFIX = "MI_Window_Glass_"
BROKEN_GLASS = "MI_Window_BrokenGlass_01_HD"
GLASS = {
    "MI_H_FutureTech_GlassDoor_01_A_HD",
    "MI_Glass_CustomDirtyA_HD",
    "MI_RoomGlass_05_HD",
    "MI_M_Commercial_Resort_Vase_05_Glass_HD",
    "MI_Generic_Vehicle_Glass_01_HD",
    "MI_H_Building_FutureTech_Helicopter_01_Glass_HD",
}


def gray(value):
    return f"[{value:g} {value:g} {value:g} 0]"


def glass_material(name, images, roles):
    if name != BROKEN_GLASS and name not in GLASS and not name.startswith(WINDOW_PREFIX):
        return None

    normal = images.get(roles.get("normal"), "")
    if name == BROKEN_GLASS:
        mask = images["T_DamageMask_2.png"]
        return f'''Layer0
{{
    shader "csgo_complex.vfx"
    F_TRANSLUCENT 1
    F_RENDER_BACKFACES 1
    F_DO_NOT_CAST_SHADOWS 1
    g_flOpacityScale "0.28"
    TextureColor "{mask}"
    TextureTranslucency "{mask}"
    TextureNormal "{normal}"
}}
'''

    transmission = 0.96
    haze = 0.07
    roughness = 0.08
    if name == "MI_Window_Glass_02_HD":
        transmission = 0.80
    elif name == "MI_Window_Glass_03_HD":
        transmission, haze, roughness = 0.75, 0.30, 0.32
    elif name == "MI_Glass_CustomDirtyA_HD":
        transmission, haze, roughness = 0.84, 0.22, 0.22
    elif name in {
        "MI_Generic_Vehicle_Glass_01_HD",
        "MI_H_Building_FutureTech_Helicopter_01_Glass_HD",
    }:
        transmission = 0.87

    normal = normal or images.get("T_Window_Glass_00_NoIBL_NR.png", "")
    normal_line = f'    TextureNormal "{normal}"\n' if normal else ""
    haze_mask = images.get("T_Blinds_01.png", gray(haze))
    return f'''Layer0
{{
    shader "csgo_glass.vfx"
    F_RENDER_BACKFACES 1
    F_DO_NOT_CAST_SHADOWS 1
    g_bFogEnabled "1"
    GlassMaskColor "[0.96 0.98 1.0 0]"
    GlassMaskTransmission "{gray(transmission)}"
    GlassMaskTranslucency "{haze_mask}"
    TextureRoughness "{gray(roughness)}"
{normal_line}}}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    materials = json.loads(args.manifest.read_text(encoding="utf-8-sig"))["materials"]
    for name, material in materials.items():
        source = glass_material(name, material["images"], material["roles"])
        if source is None:
            continue
        path = args.output / material["vmat"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        print(material["vmat"])


if __name__ == "__main__":
    main()
