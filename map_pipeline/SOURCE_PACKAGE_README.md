# DF CS2 Source Package

This archive contains the editable source and build tooling for the
Spaceport CS2 project.

## Included

- CS2 map pipeline Python, PowerShell, and Node scripts.
- Final and intermediate Source 2 VMap text sources.
- Source VMDL and VMAT definitions.
- CounterStrikeSharp plugin source and tests.
- Backend, configuration, Docker, documentation, and upstream notes.
- Server VPK multipart packaging tool.

## Excluded

The following generated or binary assets are intentionally excluded:

- Compiled VPK, VMDL_C, VMAT_C, and VTEX_C files.
- Blender and FBX model binaries.
- Source textures and EXR sky files.
- Cached build output, screenshots, crash dumps, and logs.
- The bundled Blender runtime under `.tools`.
- The ready-to-run server package under `map_build/dist`.

The complete compiled map and server package are distributed separately.

## Main Entry Points

- `map_pipeline/build_df_full.py`
- `map_pipeline/build_df_player_scale.py`
- `map_pipeline/build_df_collision_supplement.py`
- `map_pipeline/compile_nobake.ps1`
- `map_pipeline/export_df_server_map.py`
- `map_pipeline/split_vpk_chunks.mjs`
- `map_build/dist/df_spaceport_full40/source/`

CounterStrikeSharp plugin source is under `game-plugin/`. The backend is under
`backend/`. The earlier extraction scaffold is under `plugin/`.

## Notes

The map source depends on the compiled model and texture working set described
in the project README. Rebuilding from scratch requires CS2 Workshop Tools,
the source Blender scene, and the generated material/model assets.
