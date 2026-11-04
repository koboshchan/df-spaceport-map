# DF Spaceport Default Runtime

The default runtime is the restored pre-GitHub build:

```text
baseline: spaceport-pre-github-good-20261104-1224
map:      df_spaceport_player_scale_raytrace
```

The binary files are published in the repository's `default-20261105`
GitHub Release rather than committed to Git:

```text
df_spaceport_player_scale_raytrace.vpk
df_spaceport_player_scale_raytrace_000.vpk
df_spaceport_player_scale_raytrace_001.vpk
df_spaceport_player_scale_raytrace_002.vpk
```

Place all four files in:

```text
game/csgo/maps/
```

`SHA256SUMS.txt` contains the expected hashes. `addoninfo.txt` and
`df_spaceport_server.cfg` are the matching addon and server configuration.

`DEFAULT_VERSION.json` records the exact source and runtime baseline.
`play_df_spaceport_full40.ps1` defaults to the same map name.
