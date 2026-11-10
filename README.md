DF Spaceport map sources and rebuild scripts.

The organized pipeline collection lives in scripts/. It covers extraction, conversion, placement, terrain, skeletal items, foliage investigation, collision/PHYS helpers, packaging, QA, radar, rope/surface audits and inactive plugin sources. Start with docs/pipeline/README.md and its provenance manifest.

These are sanitized source templates, not a one-command rebuild. scripts/config.example.json contains empty environment-specific settings; scripts/render_template.py renders a reviewed template outside the checkout without executing it. No game assets, keys or binaries were added by this collection.

Only stable inactive snapshots were collected. The active v269/v270 foliage correction and its build folders were excluded. Historical foliage basis candidates and the original v268 installer recovery bug are explicitly marked, not represented as current working code. Python syntax and project XML were checked, but extraction, native compilation, visual parity and installation were not rerun.

Existing source staging documentation is in docs/source-staging.md. The previous baseline release README is preserved in docs/legacy-baseline.md; its coordinate conventions belong to that historical baseline and must not be substituted for the native-coordinate rebuild.

The pre-existing source/, source-tools/, map_pipeline/ and map_build/ trees remain in place. This change does not deploy a map or modify live server/client files. LICENSE is a rights notice, not a new grant over proprietary game content or third-party libraries.
