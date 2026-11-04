Loot placement candidates for df_spaceport_full40.

[loot-placements.json](loot-placements.json) contains 247 active placements, 88 excluded entries retained as metadata, original source IDs and native coordinates, and exact-case model mappings. Only active loot positions were transformed. This is data only; no map source or plugin is changed. Models are referenced by name, not bundled.

Applied coordinates are x = 0.01 * DF_Y - 6181.919922, y = -0.01 * DF_X - 4418.049805, z = 0.01 * DF_Z + 220.48600418824782. All positions remain unsnapped. [outliers-over5.json](outliers-over5.json) lists the same 24 entries marked requires_review, whose absolute sampled-surface residual exceeds 5 CS2 units.

[calibration.json](calibration.json) records the approximate horizontal fit and statistical Z evidence. The measured horizontal similarity fit used 8 points, with RMSE 0.4285 and two withheld errors of 0.6446 and 1.1314 CS2 units. The applied simpler axis-swap hypothesis has RMSE 0.5564 and withheld errors 0.5078 and 0.7735; its XY columns match those used for the Z diagnostics.

Z assumes uniform 0.01 scale and a fitted offset, not independently verified physical anchors. The offset used 180 training points and 67 withheld points; 62 withheld points agree within 2 units. Across all 247 points, 223 agree within 3 units, but p95 is 8.7740 units and the tightness gate failed. Surface agreement does not prove the correct storey. Multiple surfaces, unknown marker/asset pivots, and partial geometry coverage remain limitations.

Rotations are unknown. Extraction markers, switches and excluded entries retain native coordinates and are not calibrated. Source static labels do not guarantee a per-round spawn or fixed contents. Calibration reports retain historical pre-application warnings; source_hashes and historical_artifacts_not_included identify research provenance, not bundled files. No geometry, binary assets, downloads or map-source edits are included.
