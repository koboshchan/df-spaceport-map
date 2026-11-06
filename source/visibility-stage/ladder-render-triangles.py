import pathlib,json,struct,numpy as np
out=pathlib.Path('E:/df-v25-build-20261106/visibility-stage');data=json.load(open(out/'ladder-hit-bounds-prefilter.json'));cache={}
def triangles(path):
 if path in cache:return cache[path]
 raw=pathlib.Path(path).read_bytes();n=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+n]);b=raw[28+n:]
 def acc(i):
  a=g['accessors'][i];v=g['bufferViews'][a['bufferView']];dt={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']];k={'VEC3':3,'SCALAR':1}[a['type']];return np.ndarray((a['count'],k),dtype=dt,buffer=b,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',np.dtype(dt).itemsize*k),np.dtype(dt).itemsize)).copy()
 ts=[]
 for m in g['meshes']:
  for pr in m['primitives']:
   v=acc(pr['attributes']['POSITION']);v=v[:,[0,2,1]]*np.array([36,-36,36]);idx=acc(pr['indices']).reshape(-1,3);ts.append(v[idx])
 cache[path]=np.concatenate(ts);return cache[path]
B=np.eye(4);B[:3,:3]=np.diag([1,-1,1])/.36
for h in data:
 p=np.array([h['mark']['Position'][k] for k in 'XYZ']);normal=np.array([h['mark']['Normal'][k] for k in 'XYZ']);results=[]
 for c in h['candidates']:
  t=triangles(c['source']);C=np.array(c['matrixCS2'])@B;t=t@C[:3,:3].T+C[:3,3];a=t[:,0];u=t[:,1]-a;v=t[:,2]-a;n=np.cross(u,v);norm=np.linalg.norm(n,axis=1);n=n/np.maximum(norm[:,None],1e-30);plane=np.sum((p-a)*n,axis=1);q=p-plane[:,None]*n
  uu=np.sum(u*u,axis=1);uv=np.sum(u*v,axis=1);vv=np.sum(v*v,axis=1);w=q-a;wu=np.sum(w*u,axis=1);wv=np.sum(w*v,axis=1);den=uu*vv-uv*uv;s=(wu*vv-wv*uv)/np.maximum(den,1e-30);z=(wv*uu-wu*uv)/np.maximum(den,1e-30);inside=(s>=0)&(z>=0)&(s+z<=1)&(norm>1e-10)
  ds=np.where(inside,abs(plane),np.inf)
  for j in range(3):
   e=t[:,(j+1)%3]-t[:,j];f=np.clip(np.sum((p-t[:,j])*e,axis=1)/np.maximum(np.sum(e*e,axis=1),1e-30),0,1);ds=np.minimum(ds,np.linalg.norm(t[:,j]+f[:,None]*e-p,axis=1))
  k=int(np.argmin(ds));results.append(dict(**c,triangleIndex=k,triangle=t[k].tolist(),triangleDistance=float(ds[k]),normal=n[k].tolist(),normalAbsoluteAgreement=float(abs(n[k]@normal))))
 h['triangleCandidates']=sorted(results,key=lambda c:c['triangleDistance']);print(h['line'],[(x['rowIndex'],round(x['triangleDistance'],5),round(x['normalAbsoluteAgreement'],4),x['mesh'].split('/')[-1]) for x in h['triangleCandidates'][:4]],flush=True)
(out/'ladder-render-triangles.json').write_text(json.dumps(data,indent=2),encoding='utf8')
