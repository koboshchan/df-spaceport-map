"""Read-only framing for recovered DF shader payloads. Never executes payloads."""
import hashlib, struct
MAX_PAYLOAD=16*1024*1024
MAX_CHUNKS=256
class DecodeError(ValueError):
    pass
def sha(b): return hashlib.sha256(b).hexdigest()
def u32(b,o):
    if not isinstance(o,int) or o<0 or o+4>len(b): raise DecodeError("TRUNCATED_U32")
    return struct.unpack_from("<I",b,o)[0]
def decode_payload(b, dxbc_offset, expected_sha256):
    if len(b)>MAX_PAYLOAD: raise DecodeError("PAYLOAD_LIMIT")
    if sha(b)!=expected_sha256: raise DecodeError("HASH_MISMATCH")
    o=dxbc_offset
    if type(o) is not int or o<0 or o+32>len(b): raise DecodeError("INVALID_DXBC_OFFSET")
    if b[o:o+4]!=b"DXBC": raise DecodeError("DXBC_MAGIC")
    version=u32(b,o+20); total=u32(b,o+24); count=u32(b,o+28)
    if version!=1: raise DecodeError("UNSUPPORTED_DXBC_VERSION")
    if count>MAX_CHUNKS or count==0: raise DecodeError("CHUNK_COUNT")
    header=32+count*4
    if total<header or o+total>len(b): raise DecodeError("DXBC_BOUNDS")
    chunks=[]; intervals=[]
    for i in range(count):
        rel=u32(b,o+32+i*4)
        if rel<header or rel+8>total: raise DecodeError("CHUNK_OFFSET")
        size=u32(b,o+rel+4); end=rel+8+size
        if end>total: raise DecodeError("CHUNK_BOUNDS")
        intervals.append((rel,end))
        tag=b[o+rel:o+rel+4]
        row={"fourccHex":tag.hex(),"fourcc":tag.decode("ascii",errors="replace"),
             "offset":o+rel,"size":size,"sha256":sha(b[o+rel+8:o+end]),
             "semanticStatus":"UNSUPPORTED"}
        if tag in (b"SHDR",b"SHEX"):
            if size<8 or size%4: raise DecodeError("PROGRAM_BOUNDS")
            token=u32(b,o+rel+8); words=u32(b,o+rel+12)
            if words*4!=size: raise DecodeError("PROGRAM_LENGTH")
            row["programHeader"]={"typeCode":token>>16,"major":(token>>4)&15,"minor":token&15,"wordCount":words}
        chunks.append(row)
    for a,z in zip(sorted(intervals),sorted(intervals)[1:]):
        if a[1]>z[0]: raise DecodeError("CHUNK_OVERLAP")
    return {"schema":"df-decoder-evidence-v1","status":"PARTIAL_FRAMING_VERIFIED",
      "source":{"rawPayloadSHA256":sha(b),"bytes":len(b)},
      "customFormat":{"versionStatus":"UNSUPPORTED_UNKNOWN","prefixBytes":o,"prefixSHA256":sha(b[:o]),
         "prefixHex":b[:o].hex(),"layoutStatus":"UNSUPPORTED"},
      "dxbc":{"offset":o,"version":version,"bytes":total,"chunks":chunks,"checksumStatus":"NOT_VERIFIED"},
      "trailing":{"bytes":len(b)-o-total,"sha256":sha(b[o+total:])},
      "uniformDeclarations":{"status":"UNSUPPORTED","items":[]},
      "textureBindings":{"status":"UNSUPPORTED","items":[]},
      "operationIR":{"status":"UNSUPPORTED","items":[]},
      "permutationStatus":"UNSUPPORTED","exactDFParity":False}
