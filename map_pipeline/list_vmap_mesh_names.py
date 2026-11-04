#!/usr/bin/env python3
"""List top-level CMapMesh names and transforms from a text VMap."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from build_df_spaceport import find_block_end


def values(block: list[str], key: str, value_type: str) -> list[str]:
    pattern = re.compile(
        rf'^\s*"{re.escape(key)}"\s+"{re.escape(value_type)}"\s+"([^"]*)"'
    )
    result = []
    for line in block:
        match = pattern.match(line)
        if match:
            result.append(match.group(1))
    return result


def main() -> None:
    path = Path(sys.argv[1]).resolve()
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if line.strip() != '"CMapMesh"':
            continue
        end = find_block_end(lines, index)
        block = lines[index : end + 1]
        names = values(block, "name", "string")
        origins = values(block, "origin", "vector3")
        scales = values(block, "scales", "vector3")
        print(
            f"{index + 1}-{end + 1} "
            f"name={names[-1] if names else ''!r} "
            f"origin={origins[-1] if origins else ''!r} "
            f"scales={scales[-1] if scales else ''!r}"
        )


if __name__ == "__main__":
    main()
