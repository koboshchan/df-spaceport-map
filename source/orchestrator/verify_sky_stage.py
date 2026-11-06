import pathlib,json,hashlib,os,datetime
R=pathlib.Path("E:/df-v25-build-20261106");S=R/"sky-stage";m=json.loads((S/"manifest.json").read_text());rows=[]
for n,h in m.items():
 p=S/n;a=hashlib.sha256(p.read_bytes()).hexdigest();rows.append({"path":n,"expected":h,"actual":a,"match":a==h})
o={"success":all(x["match"] for x in rows),"files":rows,"verifiedUTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"semanticMergePending":True,"bakeFeasibility":"UNKNOWN aggregate linked-world route unproven"}
(R/"orchestrator/sky-stage-verified.json").write_text(json.dumps(o,indent=2));print(json.dumps(o))
print("COPY_PID",json.loads((R/"orchestrator/copy-process.json").read_text())["pid"])
for n in ["copy-ready.json","copy-failure.json"]:
 p=R/"orchestrator"/n
 if p.exists():print(n,p.read_text())
