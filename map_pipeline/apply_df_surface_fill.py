"""Give opaque spaceport surfaces a small, texture-driven fill in unlit areas."""
import argparse
import json
import re
from pathlib import Path

SURFACE = re.compile(
    r"vehicle|concrete|metal|wall|building|ceiling|floor|trim|road|terrain|"
    r"structure|stone|pipe|silo|dock|platform|rubber|fence", re.I
)
EXCLUDED = re.compile(
    r"decal|glass|water|foliage|leaf|litter|grass|emiss|lighting|lamp|lightstrip|"
    r"banner|sign|label|sticker|window|screen|flare", re.I
)
COLOR = re.compile(r'^\s*TextureColor "([^"]+\.(?:png|tga|jpg|jpeg))"', re.M | re.I)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "vmap", "content", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    models = set(re.findall(r'"model" "string" "(models/df_full40/c/[^"]+)"', args.vmap.read_text(encoding="utf-8-sig")))
    used = {name for cell in manifest["cells"] if cell["vmdl"] in models for name in cell["material_sources"]}
    count = 0
    for name in sorted(used):
        if not SURFACE.search(name) or EXCLUDED.search(name):
            continue
        relative = manifest["materials"][name]["vmat"]
        text = (args.content / relative).read_text(encoding="utf-8-sig")
        color = COLOR.search(text)
        if not color or re.search(r"F_TRANSLUCENT\s+1|F_ADDITIVE_BLEND\s+1", text):
            continue
        original = args.output / relative
        if 'F_SELF_ILLUM 1' in text and original.is_file():
            text = re.sub(r'g_vSelfIllumTint "[^"]+"', 'g_vSelfIllumTint "[0.65 0.65 0.65]"', text)
            original.write_text(text, encoding="utf-8")
            count += 1
            continue
        if "TextureSelfIllumMask" in text:
            continue
        text = re.sub(r'^\s*g_vEmissiveColor "[^"]+"\n', "\n", text, flags=re.M)
        properties = (
            f'\n\tF_SELF_ILLUM 1\n'
            f'\tTextureSelfIllumMask "{color[1]}"\n'
            '\tg_vSelfIllumTint "[0.65 0.65 0.65]"\n'
        )
        head, tail = text.rsplit("}", 1)
        path = args.output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(head + properties + "}" + tail, encoding="utf-8")
        count += 1
    print(f"Staged {count} opaque materials")


if __name__ == "__main__":
    main()
