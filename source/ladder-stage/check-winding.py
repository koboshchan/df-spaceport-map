import pathlib,ast
p=pathlib.Path('E:/spaceport-kat-rebuild-20261105/generate_vmap.py');tree=ast.parse(p.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))or isinstance(n,ast.FunctionDef)and n.name in ['parse','walk','cls']],type_ignores=[]),'helper','exec'))
r=parse(pathlib.Path('E:/spaceport-kat-rebuild-20261105/fixed-build/content/kat/maps/kat_phys_q001.vmap').read_text())
m=next(x for x in walk(r)if x.type=='CMapMesh');d=m['meshData'].val_elem

v=np.array([list(x)for x in next(x for x in walk(d)if x.name=='position:0')['data'].iter_vec3()])
ev=list(d['edgeVertexIndices'].iter_int());en=list(d['edgeNextIndices'].iter_int())
for start in d['faceEdgeIndices'].iter_int():
 ids=[];i=start
 while i not in ids:ids.append(i);i=en[i]
 vs=v[[ev[i]for i in ids]];n=np.cross(vs[1]-vs[0],vs[2]-vs[0]);print(float(n@(vs.mean(0)-v.mean(0))))
