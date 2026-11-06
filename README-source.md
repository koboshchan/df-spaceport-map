Reusable DF-only source staging

This branch is v25 uncompiled staging. Materials remain blocked and parity is unproven.
Reviewed v25 staging sources are published under source/. Existing df_v24 asset names are retained because source references depend on them; there is only one canonical asset tree. This is not a claim of a compiled or production-ready v25 build.

source-tools/selection.json is an explicit reviewed file allowlist, not an inventory dump.
Each entry requires relative source and destination paths, bytes, and mtime_ns.
Supply E-only source and destination roots using --source and --destination or
DF_SOURCE_ROOT and DF_SOURCE_DEST. Dry-run is the default and reads metadata only.
--apply is explicit. It never runs Git, uploads, stages, commits, or deletes files.
Use canonical source paths, not separate duplicate v24/v25 binary trees.

Plain Git is preferred. Files above 50 MiB require review; 100 MiB is the hard limit.
Oversized JSONL must use ordered lossless chunks and reassembly checksums.
Oversized binary models must not be split as fake model files.
Before publication review selected contents for credentials, AES keys, cookies,
Steam identifiers and personal receipts. Exclude compiled *_c, VPK, logs, caches,
archives and executables. Do not blanket-exclude directories containing build scripts.

Publication must use sequential reviewed batches below 1.5 GB actual pack size,
targeting about 1 GB source payload. Push and verify each batch before creating
the next commit. No LFS upload is authorized under the latest plain-Git plan.

Source manifests larger than 100 MiB are stored as ordered .jsonl.chunks directories. Use source-tools/jsonl_chunks.py join to reconstruct exact original bytes. Original manifests include SHA-256, byte counts, ordering and per-part checksums. No binary model is split.
