from pathlib import Path
import json,struct,hashlib,zlib,ctypes,collections,sys
sys.path.insert(0,'E:/df-v24-research-20261106/shader-reversal/python-libs')
import zstandard
R=Path(__file__).parent;A=Path('E:/df-extract-20261105/loot-skeletal/material-cloth-readiness/shader-proof/archives')
b=(A/'ShaderArchive-DeltaForce-PCD3D_SM5.ushaderbytecode').read_bytes()
version,count=struct.unpack_from('<II',b);start=8+38*count
assert version==1 and count==107739 and start==4094090
records=[]
for i in range(count):
 o=8+38*i;h=b[o:o+20];off,size,unc,freq=struct.unpack_from('<QIIH',b,o+20)
 records.append((h,off,size,unc,freq))
assert start+records[-1][1]+records[-1][2]==len(b)
tails=list(R.glob('*-root.native-tail.bin'));matches=[]
lookup={h:i for i,(h,off,size,unc,freq) in enumerate(records)}
prefixes={h[:4] for h in lookup}
# Match exact archive SHA1 IDs present in native material shader maps, never infer identity from texture names.
for p in tails:
 t=p.read_bytes();hits=[]
 seen=set()
 for at in range(len(t)-19):
  if t[at:at+4] not in prefixes:continue
  i=lookup.get(t[at:at+20])
  if i is None or i in seen:continue
  seen.add(i);h,off,size,unc,freq=records[i]
  hits.append({'index':i,'hash':h.hex(),'tailOffset':at,'archiveOffset':start+off,'size':size,'uncompressedSize':unc,'frequency':freq})
 matches.append({'tail':str(p),'sha256':hashlib.sha256(t).hexdigest(),'hits':hits})
(R/'archive-matches.json').write_text(json.dumps({'version':version,'count':count,'contiguous':all(records[i][1]+records[i][2]==records[i+1][1] for i in range(count-1)),'archiveSHA256':hashlib.sha256(b).hexdigest(),'materials':matches},indent=2))
out=R/'decoded';out.mkdir(exist_ok=True)
unique={h['index']:h for m in matches for h in m['hits']};receipt=[]
oodle=None
def decode(data,n):
 global oodle
 if len(data)==n:return data,'raw'
 if data[:4]==bytes.fromhex('28b52ffd'):
  d=zstandard.ZstdDecompressor().decompress(data,max_output_size=n)
  assert len(d)==n
  return d,'zstd'
 for w in [15,-15,31]:
  try:
   d=zlib.decompress(data,w)
   if len(d)==n:return d,'zlib:'+str(w)
  except zlib.error:pass
 if oodle is None:
  oodle=ctypes.CDLL('E:/df-extract-20261105/tools/oodle-data-shared.dll')
  oodle.OodleLZ_Decompress.restype=ctypes.c_ssize_t
  oodle.OodleLZ_Decompress.argtypes=[ctypes.c_void_p,ctypes.c_ssize_t,ctypes.c_void_p,ctypes.c_ssize_t,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_ssize_t,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ssize_t,ctypes.c_int]
 src=ctypes.create_string_buffer(data);dst=ctypes.create_string_buffer(n)
 result=oodle.OodleLZ_Decompress(src,len(data),dst,n,1,0,0,None,0,None,None,None,0,3)
 if result!=n:raise ValueError(('decompress',result,n,data[:8].hex()))
 return dst.raw,'oodle'
d3d=ctypes.WinDLL('d3dcompiler_47.dll')
d3d.D3DDisassemble.restype=ctypes.c_long
d3d.D3DDisassemble.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_char_p,ctypes.POINTER(ctypes.c_void_p)]
def disasm(blob):
 buf=ctypes.create_string_buffer(blob);ptr=ctypes.c_void_p()
 hr=d3d.D3DDisassemble(buf,len(blob),0,None,ctypes.byref(ptr))
 if hr:return None,hr
 vt=ctypes.cast(ptr,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
 get=ctypes.WINFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p)(vt[3])
 size=ctypes.WINFUNCTYPE(ctypes.c_size_t,ctypes.c_void_p)(vt[4])
 release=ctypes.WINFUNCTYPE(ctypes.c_ulong,ctypes.c_void_p)(vt[2])
 text=ctypes.string_at(get(ptr),size(ptr)).decode(errors='replace');release(ptr)
 return text,0
for i,h in unique.items():
 try:
  raw,method=decode(b[h['archiveOffset']:h['archiveOffset']+h['size']],h['uncompressedSize'])
  p=out/(str(i)+'.bin');p.write_bytes(raw);dx=raw.find(b'DXBC')
  row={**h,'decodedSHA256':hashlib.sha256(raw).hexdigest(),'method':method,'dxbcOffset':dx}
  if dx>=0:
   sz=struct.unpack_from('<I',raw,dx+24)[0];asm,hr=disasm(raw[dx:dx+sz]);row['disassembleHRESULT']=hr
   if asm:
    (out/(str(i)+'.asm')).write_text(asm);row['stage']=next((x.strip() for x in asm.splitlines() if x.strip().startswith(('ps_','vs_','cs_','gs_','hs_','ds_'))),None)
    row['receiverEvidence']=[x.strip() for x in asm.splitlines() if any(k in x for k in ['dcl_resource','sample','discard','SV_Target'])][:120]
  receipt.append(row)
 except Exception as e:receipt.append({**h,'error':repr(e)})
 (R/'payload-receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps({'tails':len(tails),'uniqueShaders':len(unique),'decoded':sum('decodedSHA256'in x for x in receipt),'stages':dict(collections.Counter(x.get('stage','none')for x in receipt))}))
