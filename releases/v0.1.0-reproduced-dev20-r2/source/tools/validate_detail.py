from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'work/runtime/deps'))
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
import shapely
from reconstruct_detail import alpha_region,normals,ROOT,OUT
RULES=json.loads((HERE.parents[1]/'docs/validation_rules.json').read_text(encoding='utf8'))['acceptance']

def mesh_triangles(m):
    v=np.array(m['vertices']);tri=[]
    for f in m['faces']:
        for j in range(1,len(f)-1):
            t=v[[f[0],f[j],f[j+1]]]
            if np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))>1e-10:tri.append(t)
    return np.array(tri)

def distances(points,triangles):
    best=np.full(len(points),np.inf)
    for a,b,c in triangles:
        ab=b-a;ac=c-a;n=np.cross(ab,ac);n/=np.linalg.norm(n)
        signed=(points-a)@n;proj=points-signed[:,None]*n
        v=proj-a;d00=ab@ab;d01=ab@ac;d11=ac@ac;den=d00*d11-d01*d01
        if den<=1e-24:continue
        u=(d11*(v@ab)-d01*(v@ac))/den;w=(d00*(v@ac)-d01*(v@ab))/den
        inside=(u>=0)&(w>=0)&(u+w<=1)
        dist=np.where(inside,np.abs(signed),np.inf)
        for s,e in [(a,b),(b,c),(c,a)]:
            edge=e-s;t=np.clip((points-s)@edge/(edge@edge),0,1)
            dist=np.minimum(dist,np.linalg.norm(points-(s+t[:,None]*edge),axis=1))
        best=np.minimum(best,dist)
    return best

def stats(values):
    return {'n':len(values),'mean':float(values.mean()),'median':float(np.median(values)),'p95':float(np.quantile(values,.95)),'max':float(values.max()),'coverage_at_0_15':float(np.mean(values<=.15)),'count_over_0_15':int(np.sum(values>.15))}

def reverse_samples(m,p,reference):
    rng=np.random.default_rng(1729);v=np.array(m['vertices']);groups={};basis=np.array(reference['uv_basis'])
    for f,sem in zip(m['faces'],m['semantics']):
        if 'ground' in sem:kind='inferred_ground'
        elif sem=='roof_step_or_fixture_side':kind='inferred_roof_step_or_fixture_side'
        elif 'roof' in sem:kind='observed_roof'
        else:
            uv=v[f,:2].mean(0)@basis
            seen=any(abs(uv[w['axis']]-w['coord'])<.2 and w['range'][0]-.2<=uv[1-w['axis']]<=w['range'][1]+.2 for w in reference['facade_evidence'])
            kind='observed_facade_region' if seen else 'inferred_occluded_facade'
        for j in range(1,len(f)-1):
            a,b,c=v[[f[0],f[j],f[j+1]]];area=np.linalg.norm(np.cross(b-a,c-a))/2
            if area<1e-10:continue
            count=max(3,min(500,int(np.ceil(area*5))))
            r=rng.random((count,2));s=np.sqrt(r[:,0]);samples=(1-s)[:,None]*a+(s*(1-r[:,1]))[:,None]*b+(s*r[:,1])[:,None]*c
            groups.setdefault(kind,[]).append(samples)
    tree=cKDTree(p)
    return {k:stats(tree.query(np.concatenate(samples))[0]) for k,samples in groups.items()}

def boundary_samples(poly,step=.08):
    if poly.geom_type=='MultiPolygon':return np.concatenate([boundary_samples(p,step) for p in poly.geoms])
    rings=[poly.exterior,*poly.interiors];return np.array([[p.x,p.y] for r in rings for p in [r.interpolate(t) for t in np.arange(0,r.length,step)]])

def validate(m,reference):
    source=Path(m['source']);source=source if source.is_absolute() else ROOT/source
    p=np.loadtxt(source);basis=np.array(reference['uv_basis']);q=np.c_[p[:,:2]@basis,p[:,2]]
    tri=mesh_triangles(m);res=distances(p,tri)
    edges={}
    for f in m['faces']:
        for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted([a,b]))]=edges.get(tuple(sorted([a,b])),0)+1
    volume=float(np.einsum('ij,ij->i',tri[:,0],np.cross(tri[:,1],tri[:,2])).sum()/6)
    v=np.array(m['vertices']);zarea=[]
    for f in m['faces']:
        fv=v[f];zarea.append(np.linalg.norm(np.cross(fv,np.roll(fv,-1,axis=0)).sum(0))/2)
    outline=unary_union([Polygon(t[:,:2]@basis) for t in tri if Polygon(t[:,:2]@basis).area>1e-9])
    ref=alpha_region(q[:,:2],.60)
    # Keep every observed component: discarded wings must affect the score.
    a=boundary_samples(outline);b=boundary_samples(ref)
    ab=shapely.distance(shapely.points(a),ref.boundary);ba=shapely.distance(shapely.points(b),outline.boundary)
    outline_result={'iou':outline.intersection(ref).area/outline.union(ref).area,'bidirectional_boundary_p95':float(np.quantile(np.r_[ab,ba],.95)),'boundary_max':float(max(ab.max(),ba.max())),'unsupported_area_fraction':outline.difference(ref.buffer(.15)).area/outline.area}
    patch_results=[]
    for i,e in enumerate(reference['surface_evidence']):
        co=np.array(e['coefficients']);err=np.abs(q[:,2]-(q[:,:2]@co[:2]+co[2]))
        near=err<.10
        if 'extent_uv' in e:
            lo,hi=np.array(e['extent_uv']);near&=((q[:,:2]>=lo-.08)&(q[:,:2]<=hi+.08)).all(1)
        patch_results.append({'patch':i,'kind':e['kind'],**stats(res[near])})
    facade_results=[];n,curv=normals(q,16)
    for line in reference['facade_evidence']:
        axis=line['axis'];lo,hi=line['range']
        mask=(np.abs(q[:,axis]-line['coord'])<.12)&(q[:,1-axis]>=lo)&(q[:,1-axis]<=hi)&(np.abs(n[:,2])<.3)&(np.abs(n[:,axis])>.85)
        if mask.sum():facade_results.append({**line,**stats(res[mask])})
    result={'all_points':stats(res),'roof_patches':patch_results,'observed_facades':facade_results,'outline':outline_result,'mesh_samples_to_input_by_evidence':reverse_samples(m,p,reference),'topology':{'nonmanifold_edges':sum(c!=2 for c in edges.values()),'open_edges':sum(c==1 for c in edges.values()),'degenerate_faces':int(np.sum(np.array(zarea)<1e-10)),'signed_volume':volume,'vertices':len(v),'faces':len(m['faces'])}}
    gates={'all_points':result['all_points']['p95']<=RULES['all_points_distance_p95_max'] and result['all_points']['coverage_at_0_15']>=RULES['all_points_coverage_at_0_15_min'],
        'each_roof_patch':all(r['coverage_at_0_15']>=RULES['each_supported_roof_patch_coverage_at_0_15_min'] for r in patch_results),
        'each_observed_facade':all(r['coverage_at_0_15']>=RULES['each_observed_facade_segment_coverage_at_0_15_min'] for r in facade_results),
        'outline':outline_result['iou']>=RULES['outline_iou_min'] and outline_result['bidirectional_boundary_p95']<=RULES['outline_bidirectional_distance_p95_max'] and outline_result['unsupported_area_fraction']<=RULES['unsupported_footprint_area_fraction_max'],
        'topology':all(c==2 for c in edges.values()) and volume>0 and min(zarea)>1e-10}
    gates={k:bool(v) for k,v in gates.items()}
    result['gates']=gates;result['accepted']=all(gates.values());return result,res

if __name__=='__main__':
    reports={}
    for number in ['10','1000','2000']:
        new=json.loads((OUT/f'{number}_model.json').read_text(encoding='utf8'));old=json.loads((ROOT/'work/experiments/lod2_xyz_baseline'/f'{number}_model.json').read_text(encoding='utf8'))
        old_r,_=validate(old,new);new_r,res=validate(new,new)
        reports[number]={'old':old_r,'new':new_r};np.save(OUT/f'{number}_point_distances.npy',res)
        print(number,json.dumps({name:{'all_points':r['all_points'],'gates':r['gates'],'topology':r['topology']} for name,r in [('old',old_r),('new',new_r)]}),flush=True)
    (OUT/'validation_comparison.json').write_text(json.dumps(reports,indent=2),encoding='utf8')
