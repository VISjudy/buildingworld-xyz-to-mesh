from pathlib import Path
import sys,os
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'work/runtime/deps')); os.environ['MPLCONFIGDIR']=str(HERE.parents[1]/'work/runtime/mplconfig')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import MultiPoint
from reconstruct_baseline import normals
ROOT=HERE.parents[1]
fig,axes=plt.subplots(3,4,figsize=(20,15))
for row,num in enumerate(['10','1000','2000']):
 p=np.loadtxt(ROOT/'data/inputs/LiDAR_xyz'/f'{num}.xyz')
 rect=np.array(MultiPoint(p[:,:2]).minimum_rotated_rectangle.exterior.coords)[:-1]
 u=rect[1]-rect[0]; u/=np.linalg.norm(u); basis=np.array([u,[-u[1],u[0]]]).T
 q=np.column_stack([p[:,:2]@basis,p[:,2]])
 n,c=normals(q,16)
 for col,(a,b) in enumerate([(0,1),(0,2),(1,2)]):
  ax=axes[row,col]; ax.scatter(q[:,a],q[:,b],c=q[:,2],s=3,cmap='turbo'); ax.set_aspect('equal'); ax.set_title(f'{num}: '+['UV footprint','U-Z','V-Z'][col]); ax.grid(alpha=.3)
 ax=axes[row,3]; roof=(np.abs(n[:,2])>.5)&(c<.06)
 ax.scatter(q[roof,0],q[roof,1],c=q[roof,2],s=4,cmap='turbo'); ax.set_aspect('equal'); ax.set_title(f'{num}: roof candidate XY'); ax.grid(alpha=.3)
 print(num,'axis',basis.tolist(),'bounds',q.min(0),q.max(0),flush=True)
fig.tight_layout(); fig.savefig(HERE.parents[1]/'work/audit/detail_projections.png',dpi=150)
