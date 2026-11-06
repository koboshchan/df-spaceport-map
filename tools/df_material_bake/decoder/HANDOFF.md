Reproducible handoff, limited evidence only

Workspace /home/kit/df-decoder-isolated-20261106.
Publication reserved E:/df-offline-material-workflow-20261106 branch offline-material-workflow base f771f328752e4d1c9934b69216a29065fcc5b740. Parent relays tested commits; this worker does not mutate publication or live inputs.

Run python -m unittest -v test_decoder test_optional.
Run python run_pilot.py E:/df-v25-build-20261106/material-work/raw-graph-probe/decoded E:/df-v25-build-20261106/material-work/raw-graph-probe/payload-receipt.json.
Detached launcher launch157.py runs desktop_worker157.py through scheduled task KatDFDecoder15720261106. All157 original pass PID22440 start2026-11-06T17:44:45.548574Z end2026-11-06T17:44:58.782160Z exit0.
Receipts evidence/started157.json evidence/exit157.json evidence/worker157.log.
Desktop copies E:/df-shader-decoder-20261106/{started157.json,exit157.json,worker157.log,pilot-results.json}.
Inventory and per-payload raw SHA256 evidence/fixture-manifest.json.
Historical inventory separately evidence/historical56-manifest.json. Historical56 is NOT subset of157, overlap3 identifiers only.
Tests evidence/test-receipt-next.log, 13 pass including truncations and 10000 deterministic malformed mutations.

New historical2229 optional trailer bounded structural candidate evidence/optional2229-candidate.json, raw SHA2568779d53af9648a83ef03b0200a2290de3abce7384ce964d497008af8ba5c4504.
DXBC has ISGN OSGN SHEX, no RDEF. Trailer101bytes exactly consumes key112 length6, key117 length81 and total101. Key117 has six ASCII string-array candidates: empty, View, InstancedDecalData, Material, SceneTexturesStruct, empty. These are strings observed at array indices, NOT proven UB binding slots or member declarations. Key112 six bytes uninterpreted. optional_analysis.py rejects malformed lengths/counts/terminators and never executes input.
Prefix2229 five-array candidate evidence/prefix2229-candidate.json remains unlabeled. Oracle source-order hypothesis has NOT been verified against matched UE4.27/Tencent source, so is NOT adopted as proof.
Exact Tencent serializer/version, frozen-image root boundaries, uniform members, named texture bindings and operationIR all remain UNSUPPORTED. No graph-neighborhood search or guessed layout. No compositing recipe enabled by these findings.

Publication review: imported from 2cb2fc8443ae4b5907db6bd18708004a53258dd6. Host-specific launch157.py orchestration is deliberately excluded from this public source integration. Existing detached-run receipts are historical evidence, not a newly launched task. No raw game payloads redistributed.
