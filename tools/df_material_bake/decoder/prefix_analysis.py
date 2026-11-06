"""Structural hypothesis only. Never labels array roles or claims DF schema."""
import struct,hashlib
def analyze_prefix(b):
    if len(b)<4 or len(b)>1024*1024:return {"status":"UNSUPPORTED"}
    cursor=4; arrays=[]
    while cursor<len(b):
        if cursor+4>len(b):return {"status":"UNSUPPORTED"}
        n=struct.unpack_from("<i",b,cursor)[0]
        if n<0 or n>65536 or cursor+4+4*n>len(b):return {"status":"UNSUPPORTED"}
        end=cursor+4+4*n
        arrays.append({"countOffset":cursor,"count":n,"values":list(struct.unpack_from("<"+"I"*n,b,cursor+4))})
        cursor=end
    return {"status":"STRUCTURAL_CANDIDATE_NOT_SCHEMA_PROOF","firstU32":struct.unpack_from("<I",b)[0],"arrays":arrays,"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"semanticRoles":"UNSUPPORTED","formatVersion":"UNSUPPORTED"}
