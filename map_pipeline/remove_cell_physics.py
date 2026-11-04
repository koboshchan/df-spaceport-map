#!/usr/bin/env python3
"""Remove PhysicsMeshFromRender blocks from render-only cell VMDLs."""

from __future__ import annotations

import sys
from pathlib import Path


OLD_BLOCK = """\t\t\t\tchildren =
\t\t\t\t[
\t\t\t\t\t{
\t\t\t\t\t\t_class = "PhysicsMeshFromRender"
\t\t\t\t\t\tparent_bone = ""
\t\t\t\t\t\tsurface_prop = "default"
\t\t\t\t\t\tcollision_prop = "default"
\t\t\t\t\t\ttool_material = ""
\t\t\t\t\t\trenderMeshList = [  ]
\t\t\t\t\t},
\t\t\t\t]
\t\t\t\tleave_body_collision_unmodified = false"""

NEW_BLOCK = """\t\t\t\tchildren = [  ]
\t\t\t\tleave_body_collision_unmodified = false"""


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: remove_cell_physics.py <cell directory>")
    root = Path(sys.argv[1]).resolve()
    changed = 0
    skipped = 0
    for path in root.glob("*.vmdl"):
        text = path.read_text(encoding="utf-8")
        if '"PhysicsMeshFromRender"' not in text:
            skipped += 1
            continue
        if OLD_BLOCK not in text:
            raise RuntimeError(f"physics block not found in {path}")
        path.write_text(text.replace(OLD_BLOCK, NEW_BLOCK, 1), encoding="utf-8")
        changed += 1
    print(f"CHANGED={changed} SKIPPED={skipped}")


if __name__ == "__main__":
    main()
