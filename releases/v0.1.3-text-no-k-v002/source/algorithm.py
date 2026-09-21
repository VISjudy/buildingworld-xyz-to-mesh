"""XYZ-only convex-roof prototype. No training or ground-truth evaluation.

Fits roof planes to local-normal-filtered points, clips their lower envelope
over an estimated rectangle, adds vertical walls and a provisional flat base.
This deliberately limited baseline is for simple convex roofs, not arbitrary
compound/courtyard/curved buildings. Original XYZ coordinates are preserved.
"""
from pathlib import Path
import sys, os, json, argparse, itertools
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'deps'))
os.environ.setdefault('MPLCONFIGDIR',str(HERE/'mplconfig'))
import numpy as np
from scipy.spatial import cKDTree, ConvexHull
from shapely.geometry import MultiPoint, Polygon
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT=HERE.parents[1]
OUT=ROOT/'output/lod2_xyz_baseline'

def normals(p,k=24):
    _,idx=cKDTree(p).query(p,k=min(k,len(p)),workers=-1)
    local=p[idx]; local-=local.mean(axis=1,keepdims=True)
    cov=np.einsum('nki,nkj->nij',local,local)
    val,vec=np.linalg.eigh(cov)
    return vec[:,:,0],val[:,0]/np.maximum(val.sum(axis=1),1e-12)

def planes_ransac(p,threshold=.10,point_normals=None):
    rng=np.random.default_rng(739)
    rem=np.arange(len(p)); planes=[]; supports=[]
    min_size=max(12,int(np.ceil(len(p)*.025)))
    for stage in range(8):
        if len(rem)<min_size: break
        q=p[rem]; best=np.zeros(len(q),dtype=bool)
        local_normals=None if point_normals is None else point_normals[rem]
        def compatible(coef):
            mask=np.abs(q[:,2]-(q[:,:2]@coef[:2]+coef[2]))<threshold
            if local_normals is not None:
                pn=np.array([-coef[0],-coef[1],1.]); pn/=np.linalg.norm(pn)
                mask&=np.abs(local_normals@pn)>.90
            return mask
        for _ in range(550):
            tri=q[rng.choice(len(q),3,replace=False)]
            origin=tri[:,:2].mean(axis=0)
            a=np.column_stack([tri[:,:2]-origin,np.ones(3)])
            if abs(np.linalg.det(a))<1e-5: continue
            coef=np.linalg.solve(a,tri[:,2]); coef[2]-=origin@coef[:2]
            if np.linalg.norm(coef[:2])>2: continue
            mask=compatible(coef)
            if mask.sum()>best.sum(): best=mask
        if best.sum()<min_size: break
        for _ in range(3):
            if best.sum()<min_size: break
            origin=q[best,:2].mean(axis=0)
            a=np.column_stack([q[best,:2]-origin,np.ones(best.sum())])
            coef=np.linalg.lstsq(a,q[best,2],rcond=None)[0]; coef[2]-=origin@coef[:2]
            best=compatible(coef)
        if best.sum()<min_size or np.linalg.norm(coef[:2])>2: break
        spread=np.linalg.svd(q[best,:2]-q[best,:2].mean(axis=0),compute_uv=False)
        if spread[-1]<max(1e-5,spread[0]*1e-4): break
        planes.append(coef); supports.append(int(best.sum())); rem=rem[~best]
    return np.array(planes),supports

def clip_half(poly,a,b,c):
    output=[]
    for s,e in zip(poly,np.roll(poly,-1,axis=0)):
        ds=a*s[0]+b*s[1]+c; de=a*e[0]+b*e[1]+c
        if ds<=1e-9: output.append(s)
        if (ds<0)!=(de<0): output.append(s+(e-s)*ds/(ds-de))
    return np.array(output)

def run(num):
    path=ROOT/'LiDAR_xyz'/f'{num}.xyz'; p=np.loadtxt(path)
    n,curve=normals(p)
    # Include a flat roof exactly on the quantile; zero has no elevation meaning.
    ztol=1e-9*max(1.,np.ptp(p[:,2]))
    roofmask=(np.abs(n[:,2])>.55)&(curve<.035)&(p[:,2]>=np.quantile(p[:,2],.25)-ztol)
    roof=p[roofmask]
    coef,supports=planes_ransac(roof,point_normals=n[roofmask])
    if len(coef)==0: raise RuntimeError('No roof plane supported')
    candidate_coef=coef.copy(); candidate_supports=supports[:]
    # A local lower annex must not suppress an entire higher main roof.
    # Select a supported convex main-roof hypothesis; residuals expose omitted parts.
    predicted=roof[:,:2]@coef[:,:2].T+coef[:,2]
    # Equal XY-cell mass prevents dense portions from overwhelming smaller roofs.
    cell=max(.20,float(np.linalg.norm(np.ptp(roof[:,:2],axis=0)))/48.)
    cells=np.floor((roof[:,:2]-roof[:,:2].min(axis=0))/cell).astype(np.int64)
    _,inv,counts=np.unique(cells,axis=0,return_inverse=True,return_counts=True)
    weights=1./counts[inv]; weights/=weights.sum()
    cap=max(.6,min(3.,float(np.ptp(np.quantile(roof[:,2],[.02,.98])))))
    plane_normals=np.column_stack([-coef[:,:2],np.ones(len(coef))])
    plane_normals/=np.linalg.norm(plane_normals,axis=1,keepdims=True)
    normal_error=1.-np.abs(n[roofmask]@plane_normals.T)
    best=None
    for count in range(1,len(coef)+1):
        for ids in itertools.combinations(range(len(coef)),count):
            active=np.asarray(ids)[np.argmin(predicted[:,ids],axis=1)]
            err=np.abs(predicted[np.arange(len(roof)),active]-roof[:,2])
            score=float(weights@np.minimum(err,cap)+.08*(weights@normal_error[np.arange(len(roof)),active])+.004*count)
            if best is None or score<best[0]: best=(score,ids)
    selected=list(best[1]); coef=coef[selected]; supports=[supports[i] for i in selected]
    # Smallest enclosing rectangle orientation; robust bounds reduce outliers.
    rect=np.array(MultiPoint(p[:,:2]).minimum_rotated_rectangle.exterior.coords)[:-1]
    u=(rect[1]-rect[0]); u/=np.linalg.norm(u); v=np.array([-u[1],u[0]])
    basis=np.stack([u,v],axis=1); proj=p[:,:2]@basis
    lo,hi=np.quantile(proj,[.002,.998],axis=0)
    footprint=np.array([[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]])@basis.T
    # A convex completion hull removes unsupported rectangle corners without
    # interpreting gaps in returns as holes or carving unobserved courtyards.
    inside=((proj>=lo)&(proj<=hi)).all(axis=1)
    outline=MultiPoint(p[inside,:2]).convex_hull
    if outline.geom_type=='Polygon' and outline.area>1e-5:
        outline=outline.simplify(max(.02,.001*np.linalg.norm(hi-lo)),preserve_topology=True)
        footprint=np.asarray(outline.exterior.coords)[:-1]
        if np.sum(footprint[:,0]*np.roll(footprint[:,1],-1)-footprint[:,1]*np.roll(footprint[:,0],-1))<0: footprint=footprint[::-1]
    base=float(np.quantile(p[:,2],.001))
    vertices=[]; faces=[]; semantics=[]; vi={}
    def vertex(c):
        key=tuple(np.round(c,6))
        if key not in vi: vi[key]=len(vertices); vertices.append(list(map(float,c)))
        return vi[key]
    patches=[]
    for i,plane in enumerate(coef):
        poly=footprint.copy()
        for j,other in enumerate(coef):
            if i!=j and len(poly)>=3:
                poly=clip_half(poly,*(plane-other))
        if len(poly)<3 or Polygon(poly).area<1e-5: continue
        z=poly@plane[:2]+plane[2]
        f=[vertex([*xy,h]) for xy,h in zip(poly,z)]
        f=list(dict.fromkeys(f))
        if len(f)<3: continue
        faces.append(f); semantics.append('roof'); patches.append(i)
    # Boundary edges of roof patches form eaves/gables. Shared edges are ridges.
    edges={}
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]): edges.setdefault(tuple(sorted([a,b])),[]).append((a,b))
    boundary=[ee[0] for ee in edges.values() if len(ee)==1]
    successors={a:b for a,b in boundary}
    start=boundary[0][0]; ring=[start]; cursor=successors[start]
    while cursor!=start and len(ring)<=len(boundary): ring.append(cursor); cursor=successors[cursor]
    if len(ring)!=len(boundary): raise RuntimeError('Disconnected/nonconforming roof boundary')
    bottom={a:vertex([*vertices[a][:2],base]) for a in ring}
    for a,b in boundary: faces.append([b,a,bottom[a],bottom[b]]); semantics.append('wall')
    faces.append([bottom[a] for a in ring[::-1]]); semantics.append('ground_assumed')
    vs=np.array(vertices)
    incidence={}
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]): incidence[tuple(sorted([a,b]))]=incidence.get(tuple(sorted([a,b])),0)+1
    area=0.; volume=0.
    for f in faces:
        for j in range(1,len(f)-1):
            a,b,c=vs[[f[0],f[j],f[j+1]]]
            area+=np.linalg.norm(np.cross(b-a,c-a))*.5
            volume+=np.dot(a,np.cross(b,c))/6
    residual=np.abs(np.min(roof[:,:2]@coef[:,:2].T+coef[:,2],axis=1)-roof[:,2])
    xyinside=((proj>=lo)&(proj<=hi)).all(1)
    metrics=dict(input_points=len(p),roof_candidate_points=len(roof),plane_supports=supports,
        plane_coefficients_z_eq_ax_by_c=coef.tolist(),active_roof_planes=patches,
        candidate_planes=candidate_coef.tolist(),candidate_supports=candidate_supports,selected_candidate_indices=selected,
        vertices=len(vertices),polygon_faces=len(faces),roof_faces=semantics.count('roof'),
        nonmanifold_edges=sum(c!=2 for c in incidence.values()),euler_characteristic=len(vertices)-len(incidence)+len(faces),
        signed_volume_coordinate_units_cubed=float(volume),surface_area_coordinate_units_squared=float(area),
        roof_vertical_residual_median=float(np.median(residual)),roof_vertical_residual_p95=float(np.quantile(residual,.95)),
        roof_within_020_coordinate_units=float(np.mean(residual<.2)),xy_points_within_rectangle=float(xyinside.mean()),
        prototype_fit_status='main_roof_supported' if np.mean(residual<.2)>=.8 else 'insufficient_fit_do_not_use_as_complete_reconstruction',
        provisional_base_z=base,base_rule='input z quantile 0.001; lowest observed returns, NOT verified ground',
        footprint_rule='convex completion hull of robust rectangle inliers; no empty-space carving',
        limitations=['Convex single-volume roof only; concave footprints/courtyards/extensions unsupported',
          'Planes below max(12, 2.5 percent) support omitted; lower envelope cannot represent arbitrary stepped roofs','Input unit assumed meter for Blender display only',
          'Residual is same-input fitting diagnostic, NOT ground-truth CD/ECD/NC',
          'Lowest returns do not prove terrain elevation; flat base and vertical walls are completion priors'])
    data=dict(id=str(num),source=str(path),vertices=vertices,faces=faces,semantics=semantics,metrics=metrics)
    (OUT/f'{num}_model.json').write_text(json.dumps(data,indent=2),encoding='utf8')
    with (OUT/f'{num}_lod2.obj').open('w',encoding='utf8') as f:
        f.write('# XYZ-only planar convex-roof baseline. Provisional base; no GT.\n')
        for pt in vertices: f.write('v '+' '.join(f'{v:.8f}' for v in pt)+'\n')
        for face,sem in zip(faces,semantics): f.write('g '+sem+'\n'+'f '+' '.join(str(i+1) for i in face)+'\n')
    print(num,json.dumps(metrics),flush=True)
    return data,p,roof

def preview(results):
    fig=plt.figure(figsize=(15,4.9*len(results)))
    for row,(data,p,roof) in enumerate(results):
        vs=np.array(data['vertices']); faces=data['faces']; sem=data['semantics']
        for col in range(3):
            ax=fig.add_subplot(len(results),3,3*row+col+1,projection='3d')
            if col!=1: ax.scatter(p[:,0],p[:,1],p[:,2],s=.7 if col==0 else 1,c=p[:,2],cmap='viridis',alpha=.85)
            if col!=0:
                colors=[('#c86f44' if s=='roof' else '#b9ccda') for s in sem]
                ax.add_collection3d(Poly3DCollection([vs[f] for f in faces],facecolors=colors,edgecolors='#30465c',linewidths=.8,alpha=1 if col==1 else .30))
            ax.set_title(f"LiDAR_xyz/{data['id']}.xyz | "+['Input XYZ','Planar roof + walls + base','Overlay'][col])
            ax.set(xlabel='X',ylabel='Y',zlabel='Z')
            ax.set_xlim(p[:,0].min()-1,p[:,0].max()+1); ax.set_ylim(p[:,1].min()-1,p[:,1].max()+1); ax.set_zlim(p[:,2].min()-1,p[:,2].max()+1)
            ax.set_box_aspect(np.ptp(p,axis=0)); ax.view_init(28,-55)
    fig.tight_layout(); fig.savefig(OUT/'reconstruction_comparison.png',dpi=150); plt.close(fig)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--ids',nargs='+',default=['10','1000','2000']); args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    results=[run(n) for n in args.ids]; preview(results)
