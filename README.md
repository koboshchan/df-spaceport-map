# DF Spaceport CS2

Source and build pipeline for the Counter-Strike 2 map
`df_spaceport_player_scale_raytrace`.

## Default Version

The default map is frozen to the verified pre-GitHub build:

```text
baseline: spaceport-pre-github-good-20261104-1224
map:      df_spaceport_player_scale_raytrace
built:    2026-11-04 12:24 +08:00
```

The machine-readable baseline is in
`map_build/dist/df_spaceport_full40/DEFAULT_VERSION.json`.

## Runtime Download

Download all four VPK files from the `default-20261105` GitHub Release and put
them in the same directory:

```text
game/csgo/maps/df_spaceport_player_scale_raytrace.vpk
game/csgo/maps/df_spaceport_player_scale_raytrace_000.vpk
game/csgo/maps/df_spaceport_player_scale_raytrace_001.vpk
game/csgo/maps/df_spaceport_player_scale_raytrace_002.vpk
```

Do not rename or omit any part. Verify them with the release asset
`SHA256SUMS.txt`.

```text
9522F40E5C283361045EA7B4BEC0639EF2C622A8DEB3E14E0EE9C06C50E7855B  df_spaceport_player_scale_raytrace.vpk
5EDCCEDE807C68842E903560833208333597BF29FF84AAD234356E4688C36424  df_spaceport_player_scale_raytrace_000.vpk
F5B2520FCA565C01C323D53943FD7951A9CEFB0CF7925B415B4FC3292AD48E74  df_spaceport_player_scale_raytrace_001.vpk
C3CF9742739CE11D9E6764532A22836EB2BE895434C26F274DF76B928A98A55C  df_spaceport_player_scale_raytrace_002.vpk
```

## Source

The repository includes:

- `map_pipeline/*.py`, `*.ps1`, and `*.mjs`: extraction, Blender export,
  collision, lighting, VPK packaging, and inspection tools.
- `map_pipeline/addon/df_spaceport/`: Source 2 VMap, VMAT, VMDL, model, and
  configuration source definitions.
- `map_pipeline/generated/` and `map_pipeline/source/`: intermediate and
  template VMap sources.
- `map_build/dist/df_spaceport_full40/source/`: final VMap sources used by the
  compiled maps.
- `map_build/dist/df_spaceport_full40/play_df_spaceport_full40.ps1`: default
  launcher metadata for the restored baseline.

Compiled VPK, VMAT_C, VMDL_C, FBX, texture, and Blender working assets are not
stored in normal Git history. They are distributed through Releases.

## Coordinate Conversion

For `df_spaceport_full40`, Delta Force coordinates are handled as:

```text
Blender: (Y/100, -X/100, Z/100)
Grid:    floor(Xb/40), floor(Yb/40)
Local:   Rz(-90 degrees) after subtracting the 40-unit cell origin
```

The exact implementation and constants are in
`map_pipeline/export_scene_cells.py` and `map_pipeline/build_df_full.py`.
