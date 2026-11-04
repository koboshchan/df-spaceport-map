# DF Spaceport CS2 Map Source

Source files for the Counter-Strike 2 map `df_spaceport_player_scale_raytrace`.

This repository contains only Source 2 map source data:

- `*.vmap`: map source files
- `*.vmdl`: model definitions
- `*.vmat`: material definitions
- `*.cfg`: map and server configuration files

Build scripts, analysis output, compiled resources, and additional documentation
are intentionally excluded.

## Built Map

The compiled map bundle is available from this repository's GitHub Releases.
The ZIP bundle is split into numbered parts no larger than 512 MiB.

After downloading every part, combine them in filename order and verify the ZIP:

```powershell
Get-Content .\df_spaceport_full40_latest.zip.part* -AsByteStream |
    Set-Content .\df_spaceport_full40_latest.zip -AsByteStream
```

```bash
cat df_spaceport_full40_latest.zip.part* > df_spaceport_full40_latest.zip
```

The release notes contain the SHA-256 values for both the reconstructed ZIP and
each uploaded part.
