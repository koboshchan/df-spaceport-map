#!/usr/bin/env python3
"""Add a very low warm ambient floor to opaque architectural materials."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path


INCLUDE_TOKENS = (
    "building",
    "wall",
    "concrete",
    "ground",
    "floor",
    "road",
    "metal",
    "trim",
    "structure",
    "rock",
    "terrain",
)
EXCLUDE_TOKENS = (
    "decal",
    "glass",
    "leaf",
    "leaves",
    "plant",
    "tree",
    "window",
    "lighting",
    "emissive",
    "sign",
    "sticker",
    "banner",
    "cloth",
    "water",
)
AMBIENT_LINE = '\tg_vEmissiveColor "[0.020000 0.017000 0.012000 1.000000]"'


def selected_material(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in INCLUDE_TOKENS) and not any(
        token in lowered for token in EXCLUDE_TOKENS
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--addon-root", required=True)
    parser.add_argument("--content-root", required=True)
    parser.add_argument("--backup-root", required=True)
    parser.add_argument("--filelist", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    addon_root = Path(args.addon_root).resolve()
    content_root = Path(args.content_root)
    backup_root = Path(args.backup_root).resolve()
    filelist_path = Path(args.filelist).resolve()
    report_path = Path(args.report).resolve()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = [
        record
        for name, record in manifest["materials"].items()
        if selected_material(name)
    ]

    modified = []
    skipped_existing_emission = []
    missing = []
    compile_files = []

    for record in selected:
        relative = Path(record["vmat"].replace("\\", "/"))
        source = addon_root.joinpath(*relative.parts)
        if not source.is_file():
            missing.append(str(source))
            continue

        text = source.read_text(encoding="utf-8", errors="replace")
        has_ambient_floor = AMBIENT_LINE.strip() in text
        if "TextureSelfIllumMask" in text or (
            "g_vEmissiveColor" in text and not has_ambient_floor
        ):
            skipped_existing_emission.append(record["source_name"])
            continue
        if not has_ambient_floor:
            backup = backup_root.joinpath(*relative.parts)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)

            anchor = "\tg_bFogEnabled \"1\""
            if anchor not in text:
                raise RuntimeError(f"Missing fog anchor in {source}")
            text = text.replace(anchor, anchor + "\n\n" + AMBIENT_LINE, 1)
            source.write_text(text, encoding="utf-8")

        content_path = content_root.joinpath(*relative.parts)
        content_path.parent.mkdir(parents=True, exist_ok=True)
        if not content_path.exists() or not os.path.samefile(source, content_path):
            shutil.copy2(source, content_path)
        compile_files.append(str(content_path))
        modified.append(record["source_name"])

    filelist_path.parent.mkdir(parents=True, exist_ok=True)
    filelist_path.write_text("\n".join(compile_files) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "selected": len(selected),
                "modified": len(modified),
                "skipped_existing_emission": len(skipped_existing_emission),
                "missing": missing,
                "modified_materials": modified,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"SELECTED={len(selected)} MODIFIED={len(modified)} "
        f"SKIPPED_EMISSIVE={len(skipped_existing_emission)} "
        f"MISSING={len(missing)}"
    )


if __name__ == "__main__":
    main()
