from pathlib import Path
import json,re,collections
r=Path('E:/df-extract-20261105/placements');o=Path('E:/df-v24-build-20261106/component-work')
hits=[]
for line in (r/'exports.jsonl').open(encoding='utf8'):
 x=json.loads(line);t=x.get('className','')+' '+x.get('objectPath','')
 if re.search(r'spawn|reborn|born|birth|deploy|insertion|parachute|playerinit',t,re.I):
  hits.append(x)
(o/'df-spawn-broad-index-candidates.json').write_text(json.dumps(dict(scope='existing placement index broad alternatives, not qualified spawns',count=len(hits),classCounts=dict(collections.Counter(x.get('className') for x in hits)),candidates=hits),indent=2))
print('BROAD_SPAWN_INDEX',len(hits),flush=True)
