import pathlib,json,datetime,os,traceback,collections
from decoder import decode_payload
from optional_analysis import optional_blocks
from prefix_analysis import analyze_prefix as counted_arrays
R=pathlib.Path(__file__).parent
def run():
 rows=json.loads(pathlib.Path("E:/df-v25-build-20261106/material-work/raw-graph-probe/payload-receipt.json").read_text())
 out=[]
 for row in rows:
  p=pathlib.Path("E:/df-v25-build-20261106/material-work/raw-graph-probe/decoded")/(str(row["index"])+".bin")
  b=p.read_bytes();d=decode_payload(b,row["dxbcOffset"],row["decodedSHA256"]);o=row["dxbcOffset"]
  x={"index":row["index"],"rawSHA256":row["decodedSHA256"],"prefixBytes":o,"semantics":"UNSUPPORTED"}
  try:x["prefixCandidate"]=counted_arrays(b[:o])
  except Exception as e:x["prefixCandidateRejected"]=str(e)
  try:x["optionalCandidate"]=optional_blocks(b[o+d["dxbc"]["bytes"]:])
  except Exception as e:x["optionalCandidateRejected"]=str(e)
  out.append(x)
 (R/"structural157.json").write_text(json.dumps(out,indent=2))
 print(json.dumps({"examined":len(out),"prefixCandidates":sum("prefixCandidate" in x for x in out),"optionalCandidates":sum("optionalCandidate" in x for x in out),"semanticDecodes":0}),flush=True)
if __name__=="__main__":
 (R/"structural157-start.json").write_text(json.dumps({"pid":os.getpid(),"utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}))
 code=0
 with (R/"structural157.log").open("w") as log:
  import contextlib
  with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
   try:run()
   except Exception:traceback.print_exc();code=1
 (R/"structural157-exit.json").write_text(json.dumps({"code":code,"utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}))
