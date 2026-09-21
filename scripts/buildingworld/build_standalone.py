raise SystemExit('Historical generator disabled: current pointcloud_to_mesh.py is maintained directly; see PROJECT_MEMORY.md')
"""One-time extraction of the current research prototype into a standalone CLI."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
src=(HERE/'reconstruct_detail.py').read_text(encoding='utf8')
core=src[src.index('def polygons('):src.index('def mesh_preview(')]
core=core.replace('def prepare(number):\n    p=np.loadtxt(ROOT/\'LiDAR_xyz\'/f\'{number}.xyz\');', '''def prepare(input_path):
    input_path=Path(input_path).resolve();number=input_path.stem
    p=np.loadtxt(input_path,ndmin=2)
    if p.shape[1]!=3 or len(p)<20 or not np.isfinite(p).all():
        raise ValueError('Input must contain at least 20 finite XYZ rows and exactly three columns')
    if min(np.ptp(p,axis=0)[:2])<1e-4:
        raise ValueError('Degenerate XY extent: a building footprint cannot be inferred')
   ''')
core=core.replace("return dict(id=number,p=p,", "return dict(id=number,source=str(input_path),p=p,")
core=core.replace("'source':str(ROOT/'data/inputs/LiDAR_xyz'/f\"{d['id']}.xyz\")", "'source':d['source']")
core=core.replace("patches,coefs=partition_roof(d);fp=d['footprint'];base=float(np.quantile(d['q'][:,2],.001))", "patches,coefs=partition_roof(d);fp=d['footprint'];base=float(d.get('ground_z',np.quantile(d['q'][:,2],.001)))")
core=core[:core.index('def save_model(')]
# Make assumptions and failures explicit; no arbitrary replacement geometry.
core=core.replace('    coefs=np.array(coefs)\n    residual=', "    if not coefs:raise ValueError('No supported roof plane: sparse/degenerate input or incompatible roof geometry')\n    coefs=np.array(coefs)\n    residual=")
core=core.replace("    footprint=max(polygons(footprint),key=lambda g:g.area)", "    parts=polygons(footprint)\n    if not parts:raise ValueError('No nondegenerate footprint component')\n    footprint=max(parts,key=lambda g:g.area)\n    discarded_area=float(sum(g.area for g in parts)-footprint.area)")
core=core.replace("walls=walls)", "walls=walls,discarded_footprint_area=discarded_area)")
core=core.replace("    coefs=np.array([r[0] for r in regions]);", "    if not regions:raise ValueError('Roof planes have no sufficiently supported local domains')\n    coefs=np.array([r[0] for r in regions]);")
core=core.replace("        options=sorted(available);winner=min(options", "        if not available:raise ValueError('Conflicting local roof domains: no feasible plane for one region')\n        options=sorted(available);winner=min(options")
header='''"""XYZ -> building OBJ, version 0.3.0 (review prototype).

Dependencies: numpy, scipy, shapely>=2.1 (GEOS>=3.10).
Usage: python pointcloud_to_mesh.py input.xyz output.obj
No Blender, training weights, source IDs, or ground-truth mesh required.
An exported review candidate is NOT automatically an accepted reconstruction.
"""
from pathlib import Path
import sys, os, json, itertools, argparse, time, hashlib
LOCAL_DEPS=Path(__file__).resolve().parent/'work/runtime/deps'
if LOCAL_DEPS.is_dir():sys.path.insert(0,str(LOCAL_DEPS))
import numpy as np
from scipy.spatial import cKDTree,Delaunay
from scipy.signal import find_peaks
from scipy.sparse.csgraph import connected_components
from scipy.sparse import coo_matrix
from shapely.geometry import MultiPoint,Polygon,LineString,Point,box
from shapely.ops import unary_union,polygonize
from shapely.geometry.polygon import orient
import shapely
VERSION='0.3.0'

def normals(p,k=16):
    _,idx=cKDTree(p).query(p,k=min(k,len(p)),workers=-1)
    local=p[idx];local-=local.mean(axis=1,keepdims=True)
    cov=np.einsum('nki,nkj->nij',local,local)
    val,vec=np.linalg.eigh(cov)
    return vec[:,:,0],val[:,0]/np.maximum(val.sum(axis=1),1e-12)

'''
footer='''
def topology(model):
    v=np.array(model['vertices']);edges={};area=[];volume=0.
    for face in model['faces']:
        if len(face)<3:area.append(0.);continue
        pts=v[face];area.append(float(np.linalg.norm(np.cross(pts,np.roll(pts,-1,axis=0)).sum(0))/2))
        for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted([a,b]))]=edges.get(tuple(sorted([a,b])),0)+1
        for i in range(1,len(face)-1):
            a,b,c=v[[face[0],face[i],face[i+1]]];volume+=float(np.dot(a,np.cross(b,c))/6)
    return dict(vertices=len(v),faces=len(model['faces']),nonmanifold_edges=sum(c!=2 for c in edges.values()),open_edges=sum(c==1 for c in edges.values()),degenerate_faces=sum(a<1e-10 for a in area),signed_volume=volume)

def export_obj(model,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf8') as f:
        f.write('# pointcloud_to_mesh '+VERSION+'; candidate requires geometry validation; coordinates preserved\\n')
        for p in model['vertices']:f.write('v '+' '.join(f'{v:.9f}' for v in p)+'\\n')
        for face,sem in zip(model['faces'],model['semantics']):f.write('g '+sem+'\\n'+'f '+' '.join(str(i+1) for i in face)+'\\n')

def reconstruct(input_path,output_path,ground_z=None):
    started=time.perf_counter();d=prepare(input_path)
    if ground_z is not None:d['ground_z']=float(ground_z)
    model,_=make_mesh(d)
    model['algorithm_version']=VERSION
    model['input_sha256']=hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
    model['topology']=topology(model)
    model['official_metrics']={'CD':None,'ECD':None,'NC':None,'V_Ratio':None,'F_Ratio':None,'FINAL_SCORE':None,'reason':'Ground-truth mesh and official sampling/normalization convention unavailable'}
    model['warnings']=['Ground plane inferred from lowest observed returns' if ground_z is None else 'Ground plane supplied by caller', 'Input coordinate units must match the current near-meter parameter scale','Complex compound roofs are experimental: review all point, edge and local-patch residuals']
    if d['discarded_footprint_area']>.01:model['warnings'].append('Disconnected footprint area excluded by current V2 kernel: '+str(d['discarded_footprint_area']))
    model['discarded_footprint_area']=d['discarded_footprint_area']
    if ground_z is not None:model['metrics']['base_rule']='Explicit --ground-z supplied by caller'
    model['elapsed_seconds']=time.perf_counter()-started
    model['candidate_status']='exported_pending_geometric_review'
    export_obj(model,output_path)
    Path(output_path).with_suffix('.json').write_text(json.dumps(model,indent=2),encoding='utf8')
    return model

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path,help='Whitespace-delimited XYZ point cloud')
    parser.add_argument('output',type=Path,help='Output OBJ path; same-stem JSON records evidence and limitations')
    parser.add_argument('--ground-z',type=float,help='Optional trusted ground height in source coordinates')
    parser.add_argument('--version',action='version',version=VERSION)
    args=parser.parse_args()
    try:
        model=reconstruct(args.input,args.output,args.ground_z)
        print(json.dumps({'obj':str(args.output.resolve()),'topology':model['topology'],'status':model['candidate_status'],'seconds':model['elapsed_seconds']},ensure_ascii=False))
    except Exception as exc:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        report={'status':'reconstruction_failed','error_type':type(exc).__name__,'message':str(exc),'input':str(args.input),'algorithm_version':VERSION}
        args.output.with_suffix('.error.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        print(json.dumps(report,ensure_ascii=False),file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':sys.exit(main())
'''
(ROOT/'pointcloud_to_mesh.py').write_text(header+core+footer,encoding='utf8')
compile(header+core+footer,str(ROOT/'pointcloud_to_mesh.py'),'exec')
print('Created standalone pointcloud_to_mesh.py')
