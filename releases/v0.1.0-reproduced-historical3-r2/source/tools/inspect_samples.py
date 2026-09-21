from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'work/runtime/deps'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
samples=[('xyz',i) for i in [0,1,10,100]]+[('LiDAR_xyz',i) for i in [1,2,3,10,100,500,1000,2000]]
fig=plt.figure(figsize=(16,12))
rng=np.random.default_rng(42)
for idx,(folder,num) in enumerate(samples):
    p=np.loadtxt(str(ROOT/'data/inputs'/folder/(str(num)+'.xyz')))
    print(folder,num,len(p),'min',p.min(0),'max',p.max(0),'mean',p.mean(0),flush=True)
    q=p[rng.choice(len(p),min(len(p),12000),replace=False)]
    ax=fig.add_subplot(3,4,idx+1,projection='3d')
    ax.scatter(q[:,0],q[:,1],q[:,2],c=q[:,2],s=.45,cmap='viridis',rasterized=True)
    ax.set_title(folder+'/'+str(num)+'.xyz | N='+str(len(p)),fontsize=10)
    ax.set_xlabel('X'); ax.set_ylabel('Y'); ax.set_zlabel('Z')
    ax.view_init(27,-55)
    try: ax.set_box_aspect(np.maximum(np.ptp(p,axis=0),1))
    except AttributeError: pass
fig.tight_layout()
fig.savefig(str(ROOT/'work/audit/sample_clouds.png'),dpi=145)
