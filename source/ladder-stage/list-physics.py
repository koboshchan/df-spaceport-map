import pathlib
from srctools.vpk import VPK
for a in pathlib.Path('E:/df-v24-build-20261106/ready/maps').glob('*.vpk'):
 v=VPK(a);print(a.name,[(k,v[k].size)for k in v.filenames()if any(x in k for x in ['vphys','world_physics','vwrld'])])
