DF shader evidence decoder pilot

Pure Python read-only bounded framing of recovered decompressed payloads. No execution, native library loading, shader rendering, guessed bindings or operation evaluation. Current df-decoder-evidence-v1 contract is the return object of decode_payload in decoder.py.

Input bytes and receipt-provided DXBC offset are checked against the expected SHA256. DXBC version 1, header, chunk spans, nonoverlap, shader model header and declared token word count are checked. Limits are 16MiB per payload and 256 chunks. The opaque Tencent prefix and trailing bytes are retained by hashes; custom format version, named texture bindings, uniform declarations, permutations and operation IR remain UNSUPPORTED. DXBC checksum is not validated. This is framing evidence, not a complete Tencent decoder or DF parity.

Tests use synthetic bytes only and include every truncation, overflow-shaped fields, negative offsets, unknown version, hash mismatch and 10000 deterministic mutations. Run python -m unittest -v test_decoder test_optional. Game payloads are private local fixtures, not redistributed. Upstream compression metadata is attributed to its receipt, not reverified by this pilot.

Verified desktop one-shot detached run 2026-11-06T17:43:38Z PID159148 exited0, all10 tests and56 prior recovered Deferred shader payload framings passed. The later 157-payload run is separately recorded in evidence/fixture-manifest.json and evidence/worker157.log. Historical 56 coverage is not a subset of that inventory. No active map/build content changes.
