import pathlib,json,hashlib,collections,datetime
R=pathlib.Path("E:/df-v25-build-20261106");V=R/"visibility-stage/exclusion-manifest.json";S=pathlib.Path("E:/df-v24-build-20261106/component-work/final-combined-placements.jsonl")
assert hashlib.sha256(V.read_bytes()).hexdigest()=="b0034f6f263cbe03c49915266d0148668427b0ffdf317eb025ef43a5622e317b"
rows=[json.loads(l) for l in S.open(encoding="utf8")]
idx=collections.defaultdict(list)
for i,x in enumerate(rows):idx[(x["objectPath"],x.get("instanceIndex"))].append((i,x))
out=[];bad=[]
for e in json.loads(V.read_text())["exclusions"]:
 key=(e["objectPath"],e.get("instanceIndex"));hits=idx[key]
 ok=len(hits)==1 and hits[0][0]==e["rowIndex"] and hits[0][1]["meshObjectPath"]==e["mesh"]
 row={"objectPath":key[0],"instanceIndex":key[1],"matches":len(hits),"rowIndex":e["rowIndex"],"exactKeyRowMeshMatch":ok}
 out.append(row)
 if not ok:bad.append(row)
receipt={"success":not bad,"count":len(out),"bad":bad,"rows":out,"sourceSHA256":hashlib.sha256(S.read_bytes()).hexdigest(),"manifestSHA256":hashlib.sha256(V.read_bytes()).hexdigest(),"verification":"source only; no merge/compile claim","atUTC":datetime.datetime.now(datetime.timezone.utc).isoformat()}
(R/"orchestrator/visibility-key-match.json").write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k!="rows"}))
