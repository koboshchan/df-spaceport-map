import pathlib,json,hashlib,datetime,traceback
R=pathlib.Path('E:/df-v25-build-20261106');O=R/'orchestrator/nonmaterial-stage';O.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(O/n).write_text(json.dumps(x,indent=2))
try:
 ready=json.loads((R/'visibility-stage/READY-source-exclusions.json').read_text())
 base=R/'visibility-stage/exclusion-manifest.json';assert sha(base)==ready['baseSHA256']
 ex=json.loads(base.read_text())['exclusions'];rows=[json.loads(l) for l in (R/'component-work/final-combined-placements.jsonl').open(encoding='utf8')]
 decisions=[]
 for x in ex:
  r=rows[x['rowIndex']];assert r['objectPath']==x['objectPath'] and r.get('instanceIndex')==x.get('instanceIndex')
  assert r['meshObjectPath']==x['mesh']
  decisions.append({'rowIndex':x['rowIndex'],'objectPath':r['objectPath'],'instanceIndex':r.get('instanceIndex'),'mesh':r['meshObjectPath'],'renderExclude':True,'collisionExclude':bool(x['collision_exclude']),'baseDecision':x})
 for x in ready['additionalEmergency']:
  r=rows[x['rowIndex']];assert r['objectPath']==x['objectPath']
  decisions.append(dict(x,instanceIndex=r.get('instanceIndex'),mesh=r['meshObjectPath']))
 assert sum(x['collisionExclude'] for x in decisions)==358
 assert sum(not x['collisionExclude'] for x in decisions)==2
 assert len(decisions)==360 and len({x['rowIndex'] for x in decisions})==360
 save('exact-visibility-decisions.json',{'count':360,'sourceSHA256':sha(R/'component-work/final-combined-placements.jsonl'),'decisions':decisions,'noSourceRowsEdited':True,'compiledAbsenceNotYetVerified':True})
 p=R/'orchestrator/parent-candidate-verified.json';rec=json.loads(p.read_text());assert sha(pathlib.Path(rec['candidate']))==rec['SHA256'];assert sha(R/'orchestrator/spawn32-validated-source.json')==rec['spawnSnapshotSHA256']
 frozen=[]
 for root in ['sky-stage','ladder-stage/full-v25-handoff','ladder-stage/world-collision-candidate']:
  for f in (R/root).rglob('*'):
   if f.is_file():frozen.append({'path':str(f),'bytes':f.stat().st_size,'sha256':sha(f)})
 save('frozen-inputs.json',frozen)
 save('validation.json',{'success':True,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'visibility':360,'parentReceiptVerified':True,'frozenFiles':len(frozen),'notPromoted':True,'notCompiled':True,'centralLock':'49f09f11','materialOwner':'9b9f7b1c exclusive frozen table parse','independentReviewer':'d007b190 receipt review only','materialGate':'BLOCKED no guessed bindings'})
 print('PASS',len(frozen))
except BaseException:
 save('validation.json',{'success':False,'traceback':traceback.format_exc(),'notPromoted':True});raise
