"""Read-only D3DDisassemble declaration evidence; no Tencent field semantics."""
import pathlib,json,hashlib,ctypes,re,datetime,os,contextlib,traceback
from decoder import decode_payload
from optional_analysis import optional_blocks
R=pathlib.Path(__file__).parent
SOURCE=pathlib.Path("E:/df-v25-build-20261106/material-work/raw-graph-probe")
def declarations(text):
 rows=[];unknown=[]
 for line in text.splitlines():
  line=line.strip()
  if not line.startswith("dcl_"):continue
  # Keep every declaration as evidence. Count ONLY explicit SM5 immediate register declarations.
  kind=None;pattern=None
  if line.startswith("dcl_constantbuffer "):kind="cb";pattern=r"\bcb(\d+)\[(\d+)\]"
  elif line.startswith("dcl_sampler "):kind="sampler";pattern=r"\bs(\d+)\b"
  elif line.startswith(("dcl_resource_","dcl_resource ")):kind="srv";pattern=r"\bt(\d+)\b"
  elif line.startswith("dcl_uav_"):kind="uav";pattern=r"\bu(\d+)\b"
  if kind:
   m=re.search(pattern,line,re.IGNORECASE)
   if not m:unknown.append(line);continue
   row={"kind":kind,"register":int(m[1]),"line":line}
   if kind=="cb":row["float4Vectors"]=int(m[2])
   rows.append(row)
 stats={}
 for kind in ["cb","sampler","srv","uav"]:
  regs=sorted(set(x["register"] for x in rows if x["kind"]==kind))
  stats[kind]={"registers":regs,"uniqueRegisterCount":len(regs),"registerSpan":max(regs)+1 if regs else 0,
               "declarationLines":sum(x["kind"]==kind for x in rows)}
 return {"rows":rows,"metrics":stats,"unparsedResourceDeclarations":unknown}
def run():
 dll=ctypes.WinDLL("d3dcompiler_47.dll"); fn=dll.D3DDisassemble
 fn.restype=ctypes.c_long;fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_char_p,ctypes.POINTER(ctypes.c_void_p)]
 out=[]
 for row in json.loads((SOURCE/"payload-receipt.json").read_text()):
  b=(SOURCE/"decoded"/(str(row["index"])+".bin")).read_bytes()
  d=decode_payload(b,row["dxbcOffset"],row["decodedSHA256"]);off=row["dxbcOffset"];size=d["dxbc"]["bytes"]
  blob=b[off:off+size];buf=ctypes.create_string_buffer(blob);ptr=ctypes.c_void_p()
  hr=fn(buf,len(blob),0,None,ctypes.byref(ptr))
  if hr:raise ValueError(("D3DDisassemble",row["index"],hr))
  vt=ctypes.cast(ptr,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
  get=ctypes.WINFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p)(vt[3]);sz=ctypes.WINFUNCTYPE(ctypes.c_size_t,ctypes.c_void_p)(vt[4]);release=ctypes.WINFUNCTYPE(ctypes.c_ulong,ctypes.c_void_p)(vt[2])
  try:asm=ctypes.string_at(get(ptr),sz(ptr)).rstrip(b"\x00").decode("utf-8")
  finally:release(ptr)
  parsed=declarations(asm)
  optional=optional_blocks(b[off+size:])
  p=[x["uninterpretedBytes"] for x in optional["blocks"] if x["keyByte"]==112]
  if len(p)!=1 or len(p[0])!=6:raise ValueError(("p_bounds",row["index"]))
  out.append({"index":row["index"],"rawSHA256":row["decodedSHA256"],"dxbcSHA256":hashlib.sha256(blob).hexdigest(),"disassemblySHA256":hashlib.sha256(asm.encode()).hexdigest(),"stage":row.get("stage"),"pBytes":p[0],"declarations":parsed,"pFieldSemantics":"UNSUPPORTED","namedBindings":"UNSUPPORTED"})
 if len(out)!=157:raise ValueError("INVENTORY_COUNT")
 comparisons=[]
 for byte in range(6):
  for kind in ["cb","sampler","srv","uav"]:
   for metric in ["uniqueRegisterCount","registerSpan"]:
    matches=[];counter=[]
    for x in out:
     value=x["declarations"]["metrics"][kind][metric]
     item={"index":x["index"],"pByte":x["pBytes"][byte],"declarationMetric":value}
     (matches if x["pBytes"][byte]==value else counter).append(item)
    comparisons.append({"pByteIndex":byte,"kind":kind,"metric":metric,"matches":len(matches),"counterexamples":counter,"inferenceStatus":"CORRELATION_ONLY_NOT_FIELD_SEMANTICS"})
 report={"schema":"df-p-declaration-hypothesis-v1","examined":len(out),"semanticDecodes":0,"sourceVersionMatch":"UNSUPPORTED","frozenRoot":"UNSUPPORTED","stockReferenceMismatch":"DF p length6 versus stock reference fields totaling7 without padding","records":out,"comparisons":comparisons}
 (R/"declarations157.json").write_text(json.dumps(report,indent=2))
 print(json.dumps({"examined":len(out),"unparsed":sum(len(x["declarations"]["unparsedResourceDeclarations"]) for x in out),"perfectEqualities":[{k:v for k,v in c.items() if k!="counterexamples"} for c in comparisons if c["matches"]==157],"semanticDecodes":0}),flush=True)
if __name__=="__main__":
 (R/"declarations157-start.json").write_text(json.dumps({"pid":os.getpid(),"utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}))
 code=0
 with (R/"declarations157.log").open("w") as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
  try:run()
  except Exception:traceback.print_exc();code=1
 (R/"declarations157-exit.json").write_text(json.dumps({"code":code,"utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}))
