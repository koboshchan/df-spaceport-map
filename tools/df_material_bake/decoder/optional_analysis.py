"""Bounded optional-data structural candidate. Key semantics remain unverified."""
import struct, hashlib
from decoder import DecodeError
def optional_blocks(t):
    if len(t)<4 or len(t)>1024*1024: raise DecodeError("OPTIONAL_BOUNDS")
    if struct.unpack_from("<I",t,len(t)-4)[0]!=len(t):
        raise DecodeError("OPTIONAL_TOTAL")
    p=0; out=[]
    while p<len(t)-4:
        if p+5>len(t)-4: raise DecodeError("OPTIONAL_HEADER")
        k=t[p]; n=struct.unpack_from("<I",t,p+1)[0]; end=p+5+n
        if end>len(t)-4: raise DecodeError("OPTIONAL_LENGTH")
        d=t[p+5:end]
        row={"keyByte":k,"offset":p,"bytes":n,"sha256":hashlib.sha256(d).hexdigest(),
             "semanticStatus":"UNSUPPORTED_UNMATCHED_SERIALIZER"}
        if k==117:
            try: row["candidateStringArray"]=strings(d)
            except DecodeError: row["candidateStringArrayStatus"]="REJECTED"
        if k==112: row["uninterpretedBytes"]=list(d)
        out.append(row);p=end
    return {"status":"STRUCTURAL_CANDIDATE_NOT_SCHEMA_PROOF","blocks":out,
            "bytes":len(t),"sha256":hashlib.sha256(t).hexdigest()}
def strings(d):
    if len(d)<4:raise DecodeError("STRING_COUNT")
    count=struct.unpack_from("<i",d)[0]
    if not 0<=count<=256:raise DecodeError("STRING_COUNT")
    p=4; out=[]
    for i in range(count):
        if p+4>len(d):raise DecodeError("STRING_HEADER")
        n=struct.unpack_from("<i",d,p)[0];p+=4
        if not 0<=n<=65536 or p+n>len(d):raise DecodeError("STRING_LENGTH")
        b=d[p:p+n];p+=n
        if n and b[-1]!=0:raise DecodeError("STRING_TERMINATOR")
        try:s=b[:-1].decode("ascii") if n else ""
        except UnicodeError:raise DecodeError("STRING_ENCODING")
        out.append({"arrayIndex":i,"text":s,"bindingSlotStatus":"UNSUPPORTED"})
    if p!=len(d):raise DecodeError("STRING_TRAILING")
    return out
