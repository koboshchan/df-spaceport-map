from pathlib import Path
import struct,json
ROOT=Path(__file__).parent
def parse(name):
 b=(ROOT/(name+'.native-tail.bin')).read_bytes();o=4
 def read(fmt):
  nonlocal o
  v=struct.unpack_from('<'+fmt,b,o);o+=struct.calcsize('<'+fmt);return v[0] if len(v)==1 else list(v)
 n=read('i');names=[]
 for i in range(n):
  l=read('i');names.append(b[o:o+l].decode().rstrip(chr(0)));o+=l+4
 locstart=o+4;count=read('i');assert 0<count<=64
 locations=[read('IBBB') for i in range(count)];total=read('i');base=o
 def fn():
  i=read('i');num=read('i');assert 0<=i<len(names),(o,i,num)
  return names[i] if num==0 else names[i]+'_'+str(num-1)
 def expr(depth=0):
  assert depth<32
  start=o;t=fn();d={'offset':start,'type':t}
  if t.endswith(('VectorParameter','ScalarParameter')):
   d['name']=fn();d['association']=read('b');d['index']=read('i');d['default']=read('4f' if t.endswith('VectorParameter') else 'f')
  elif t.endswith('AppendVector'):d['A']=expr(depth+1);d['B']=expr(depth+1);d['numComponentsA']=read('I')
  elif t.endswith('ComponentSwizzle'):d['X']=expr(depth+1);d['swizzle']=read('5b')
  elif t.endswith('FoldedMath'):d['A']=expr(depth+1);d['B']=expr(depth+1);d['op']=read('B');d['valueType']=read('I')
  elif t.endswith('Constant'):d['value']=read('4f');d['valueType']=read('B')
  elif t.endswith('TextureParameter'):
   d['textureIndex']=read('i');d['samplerSource']=read('i');d['name']=fn();d['association']=read('b');d['index']=read('i')
  else:raise ValueError((start,t))
  d['end']=o;return d
 results=[]
 for i,loc in enumerate(locations):
  o=base+loc[0]+84; ln=read('i'); o+=abs(ln)*(2 if ln<0 else 1);d={'resourceIndex':i,'location':loc,'base':base+loc[0],'uniformStart':o}
  try:
   for label in ['vectors','scalars','textures','cubeTextures','volumeTextures','virtualTextures']:
    count=read('i');assert 0<=count<200,(o,count)
    d[label]=[expr() for j in range(count)]
  except Exception as e:d['parseError']=repr(e)
  d['end']=o;d['followingBytes']=b[o:o+128].hex();results.append(d)
 (ROOT/(name+'.uniforms.json')).write_text(json.dumps({'names':names,'base':base,'resources':results},indent=2))
 return results

if __name__=='__main__':
 print(parse('props-root'))
