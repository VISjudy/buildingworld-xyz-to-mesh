from inspect_detail import HERE,ROOT
import numpy as np
from shapely.geometry import MultiPoint
from scipy.signal import find_peaks
from reconstruct_baseline import normals
from scipy.spatial import cKDTree
import json
out={}
for num in ['10','1000','2000']:
 p=np.loadtxt(ROOT/'data/inputs/LiDAR_xyz'/f'{num}.xyz'); rect=np.array(MultiPoint(p[:,:2]).minimum_rotated_rectangle.exterior.coords)[:-1]
 u=rect[1]-rect[0]; u/=np.linalg.norm(u); basis=np.array([u,[-u[1],u[0]]]).T
 q=np.column_stack([p[:,:2]@basis,p[:,2]]); n,c=normals(q,16)
 walls=(np.abs(n[:,2])<.25)&(c<.08)
 r={'wall_points':int(walls.sum()),'wall_lines':[]}
 for a in [0,1]:
  # Coordinate concentration supported by wall normals aligned to this axis.
  w=q[walls&(np.abs(n[:,a])>.9)]
  bins=np.arange(q[:,a].min()-.1,q[:,a].max()+.15,.04); hist,edges=np.histogram(w[:,a],bins)
  peaks,_=find_peaks(hist,height=8,distance=5)
  for i in peaks:
   center=(edges[i]+edges[i+1])*.5; pp=w[np.abs(w[:,a]-center)<.10]
   r['wall_lines'].append({'axis':a,'coord':float(np.median(pp[:,a])),'n':len(pp),'other_range':np.quantile(pp[:,1-a],[0,.5,1]).tolist(),'zrange':np.quantile(pp[:,2],[0,.5,1]).tolist()})
 print(num,r,flush=True); out[num]=r
(HERE.parents[1]/'work/audit/wall_evidence.json').write_text(json.dumps(out,indent=2),encoding='utf8')
