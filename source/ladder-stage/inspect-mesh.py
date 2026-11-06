import pathlib,ast
p=pathlib.Path('E:/spaceport-kat-rebuild-20261105/generate_vmap.py');tree=ast.parse(p.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))or isinstance(n,ast.FunctionDef)and n.name in ['parse','walk','cls']],type_ignores=[]),'helper','exec'))
r=parse(pathlib.Path('E:/spaceport-kat-rebuild-20261105/fixed-build/content/kat/maps/kat_phys_q001.vmap').read_text())
m=next(x for x in walk(r)if x.type=='CMapMesh');d=m['meshData'].val_elem
for x in walk(d):
 print(x.type,x.name,[(k,str(v)[:150])for k,v in x.items()])
