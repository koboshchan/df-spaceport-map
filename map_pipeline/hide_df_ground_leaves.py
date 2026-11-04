"""Hide ground-only leaf scatter with a black additive material."""
import argparse
import json
import re
import struct
import zlib
from pathlib import Path

GROUND_LEAF = re.compile(
    r"MI_(?:H_FutureTech_Resort_litter_01|H_IceLand_Props_litter_01|"
    r"DECOR_(?:LeavesPalm_0[12]|LeavesThin_0[12]|PopulusLeaves_01|LeavesConifers_01|"
    r"DatePalm_Dry_0[123]|GrassDebris_(?:Dry|Less|More|Thin)_01)_Leaf)_HD",
    re.IGNORECASE,
)
MASK = "materials/df_full_v2/t/df_hidden_ground_leaf.png"
MATERIAL = f"""Layer0
{{
    shader "csgo_complex.vfx"
    F_ADDITIVE_BLEND 1
    F_TRANSLUCENT 1
    g_flOpacityScale "0.0"
    TextureColor "{MASK}"
}}
"""


def png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    materials = [m["vmat"] for name, m in manifest["materials"].items() if GROUND_LEAF.fullmatch(name)]
    if len(materials) != 15:
        raise ValueError(f"Expected 15 dedicated leaf materials, found {len(materials)}")
    texture = args.output / MASK
    texture.parent.mkdir(parents=True, exist_ok=True)
    texture.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 6, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(bytes(4 * (1 + 4 * 4))))
        + png_chunk(b"IEND", b"")
    )
    for relative in materials:
        path = args.output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(MATERIAL, encoding="utf-8")
        print(relative)


if __name__ == "__main__":
    main()
