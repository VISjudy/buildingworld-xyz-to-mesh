"""Check candidate cross-split geometric overlap; never use it for model fitting."""
from pathlib import Path
from collections import defaultdict
import csv, json
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
rows=list(csv.DictReader((HERE.parents[1]/'work/audit/pointcloud_inventory.csv').open(encoding='utf8')))
train=defaultdict(list)
for r in rows:
    if r['split']=='xyz': train[int(r['points'])].append(r)
candidates=[]
for q in rows:
    if q['split']!='LiDAR_xyz': continue
    for p in train[int(q['points'])]:
        if abs(float(p['z_span'])-float(q['z_span']))<1e-7 and min(float(p['x_span']),float(p['y_span']))>1:
            candidates.append((p['name'],q['name']))
checks=[]
for a,b in candidates[:10]:
    p=np.loadtxt(ROOT/'data/inputs/xyz'/a); q=np.loadtxt(ROOT/'data/inputs/LiDAR_xyz'/b)
    pc=p-p.mean(0); qc=q-q.mean(0)
    u,s,vt=np.linalg.svd(pc.T@qc); rot=u@vt
    checks.append(dict(train=a,test=b,points=len(p),orthogonal_alignment_rmse=float(np.sqrt(np.mean(np.sum((pc@rot-qc)**2,axis=1)))),determinant=float(np.linalg.det(rot))))
r=dict(same_point_count_and_z_span_candidates=len(candidates),criteria='Equal point count and abs z span difference < 1e-7; XY spans > 1 in training. Candidates are NOT all proven duplicates.',first_ten_verified=checks)
(HERE.parents[1]/'work/audit/cross_split_overlap_check.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print(json.dumps(r,indent=2))
