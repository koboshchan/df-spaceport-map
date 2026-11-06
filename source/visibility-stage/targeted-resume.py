import pathlib,json,traceback,time,os
o=pathlib.Path('E:/df-v25-build-20261106/visibility-stage');base=pathlib.Path('E:/df-extract-20261105/placements/validation/resolution/metadata')
try:
 rows=[json.loads(l) for l in open('E:/df-v24-build-20261106/component-work/final-combined-placements.jsonl',encoding='utf8')]
 unknown=[x for x in rows if not x.get('sourceJson')];idx={x['objectPath']:x for x in map(json.loads,open(base/'objects.jsonl',encoding='utf8'))};found={};miss=[]
 def load(key):
  if key in found:return found[key]
  z=idx.get(key)
  if not z:return None
  p=base/z['metadata'];v=json.load(open(p,encoding='utf8'));found[key]=dict(index=z,file=str(p),object=v);return found[key]
 for x in unknown:
  key=x['objectPath'];owner=x.get('actor') or key.rsplit('.',1)[0]
  v=load(key);a=load(owner)
  if not v:miss.append(dict(component=key,owner=owner,ownerFound=bool(a)))
 for iteration in range(6):
  before=len(found)
  for f in list(found.values()):
   z=f['index']
   for key in [z.get('template'),z.get('super'),z.get('outer')]:
    if isinstance(key,str):load(key)
  if before==len(found):break
 (o/'targeted-owner-inheritance-index.json').write_text(json.dumps(dict(totalUnknown=len(unknown),resolvedObjects=found,componentMisses=miss),ensure_ascii=False),encoding='utf8')
 (o/'targeted-resume-exit.json').write_text(json.dumps(dict(exitCode=0,objects=len(found),misses=len(miss),pid=os.getpid())),encoding='utf8')
 print('DONE',len(found),len(miss),flush=True)
except:
 (o/'targeted-resume-error.txt').write_text(traceback.format_exc(),encoding='utf8')
 (o/'targeted-resume-exit.json').write_text(json.dumps(dict(exitCode=1,errorLog=str(o/'targeted-resume-error.txt'))),encoding='utf8')
 raise
