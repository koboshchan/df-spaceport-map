#!/usr/bin/env python3
"""Export source images that are not referenced by generated VMAT files."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


EXTENSIONS = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "OPEN_EXR": ".exr",
    "HDR": ".hdr",
    "TARGA": ".tga",
    "TIFF": ".tif",
}


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) != 2:
        raise SystemExit("usage: export_orphan_images.py -- <names> <output dir>")
    names = set(Path(args[0]).read_text(encoding="utf-8").splitlines())
    output_root = Path(args[1]).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    exported = 0
    for image in bpy.data.images:
        if image.name not in names or image.name == "Render Result":
            continue
        extension = EXTENSIONS.get(image.file_format, ".png")
        safe_name = "".join(
            character if character.isalnum() or character in "._-" else "_"
            for character in image.name
        )
        safe_name = str(Path(safe_name).with_suffix(""))
        destination = output_root / f"{safe_name}{extension}"
        packed = image.packed_file
        if packed is not None and hasattr(packed, "data"):
            destination.write_bytes(bytes(packed.data))
        else:
            previous_format = image.file_format
            image.file_format = "PNG" if extension == ".png" else previous_format
            image.save_render(str(destination), scene=bpy.context.scene)
            image.file_format = previous_format
        print(f"EXPORTED_IMAGE={destination}")
        exported += 1
    print(f"EXPORTED={exported}")


if __name__ == "__main__":
    main()
