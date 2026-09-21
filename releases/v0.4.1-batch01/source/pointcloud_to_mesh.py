"""XYZ -> building OBJ, version 0.4.1 (review prototype).

Dependencies: numpy, scipy, shapely>=2.1, mapbox-earcut.
Usage: python pointcloud_to_mesh.py input.xyz output.obj
No Blender, training weights, source IDs, or ground-truth mesh required.
An exported review candidate is NOT automatically an accepted reconstruction.
"""
from pathlib import Path
import sys, os, json, itertools, argparse, time, hashlib
LOCAL_DEPS=Path(__file__).resolve().parent/'analysis/buildingworld/deps'
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
import mapbox_earcut
VERSION='0.4.1'

def triangulate_polygon(pg):
    """Earcut preserves polygon boundaries and holes without GEOS CDT stalls."""
    pg=shapely.make_valid(pg) if not pg.is_valid else pg
    triangles=[]
    for part in polygons(pg):
        rings=[np.array(part.exterior.coords)[:-1],*[np.array(r.coords)[:-1] for r in part.interiors]]
        cleaned=[]
        for ring in rings:
            keep=np.r_[True,np.linalg.norm(np.diff(ring,axis=0),axis=1)>1e-8]
            ring=ring[keep]
            if len(ring)>=3:cleaned.append(ring)
        if not cleaned:continue
        vertices=np.ascontiguousarray(np.concatenate(cleaned),dtype=np.float64)
        ends=np.cumsum([len(r) for r in cleaned]).astype(np.uint32)
        indices=mapbox_earcut.triangulate_float64(vertices,ends).reshape(-1,3)
        for ids in indices:
            tri=Polygon(vertices[ids])
            if tri.area>1e-12:triangles.append(tri)
    return triangles

def normals(p,k=16):
    _,idx=cKDTree(p).query(p,k=min(k,len(p)),workers=-1)
    local=p[idx];local-=local.mean(axis=1,keepdims=True)
    cov=np.einsum('nki,nkj->nij',local,local)
    val,vec=np.linalg.eigh(cov)
    return vec[:,:,0],val[:,0]/np.maximum(val.sum(axis=1),1e-12)

def polygons(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    return [p for x in getattr(g,'geoms',[]) for p in polygons(x)]

def alpha_region(xy,radius=.55):
    xy=np.unique(xy,axis=0)
    if len(xy)<4:return MultiPoint(xy).convex_hull
    dt=Delaunay(xy); t=xy[dt.simplices]
    a=np.linalg.norm(t[:,1]-t[:,0],axis=1); b=np.linalg.norm(t[:,2]-t[:,1],axis=1); c=np.linalg.norm(t[:,0]-t[:,2],axis=1)
    ab=t[:,1]-t[:,0];ac=t[:,2]-t[:,0];twice=np.abs(ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0])
    rad=a*b*c/np.maximum(2*twice,1e-12)
    g=unary_union([Polygon(v) for v in t[rad<radius]])
    if g.is_empty: return MultiPoint(xy).convex_hull
    g=g.buffer(.10,join_style=2).buffer(-.10,join_style=2)
    return unary_union([Polygon(p.exterior) if p.area<.5 else p for p in polygons(g) if p.area>.02])

def ortho_polygon(g,tol=.18):
    # Orthogonalize only already axis-aligned edges; preserve oblique evidence.
    parts=[]
    for pg in polygons(g):
        pg=pg.simplify(tol,preserve_topology=True)
        def ring(coords):
            original=np.array(coords)[:-1];xy=original.copy(); dirs=np.roll(xy,-1,axis=0)-xy
            # Remove sampling-rounded corners when a short bevel only joins
            # two strong perpendicular boundary directions.
            remove=set(); replacement={}
            for i,dd in enumerate(dirs):
                prev=dirs[(i-1)%len(dirs)]; nxt=dirs[(i+1)%len(dirs)]
                if .03<np.linalg.norm(dd)<1.25 and min(abs(dd))>.06:
                    pv=int(abs(prev[1])>abs(prev[0])); nv=int(abs(nxt[1])>abs(nxt[0]))
                    if pv!=nv and max(abs(prev))>3*min(abs(prev)) and max(abs(nxt))>3*min(abs(nxt)):
                        pt=xy[i].copy();pt[pv]=xy[(i+1)%len(xy),pv]
                        replacement[i]=pt;remove.add((i+1)%len(xy))
            if remove:
                xy=np.array([replacement.get(i,p) for i,p in enumerate(xy) if i not in remove]);dirs=np.roll(xy,-1,axis=0)-xy
                if len(xy)<3:return original.tolist()
            ori=[]; locations=[]
            for a,d in zip(xy,dirs):
                if abs(d[0])<abs(d[1])*.32:ori.append(0); locations.append(float(a[0]+d[0]/2))
                elif abs(d[1])<abs(d[0])*.32:ori.append(1); locations.append(float(a[1]+d[1]/2))
                else:ori.append(-1);locations.append(0)
            out=[]
            for i in range(len(xy)):
                pt=xy[i].copy()
                for j in [(i-1)%len(xy),i]:
                    if ori[j]>=0:pt[ori[j]]=locations[j]
                out.append(pt)
            candidate=Polygon(out)
            if not candidate.is_valid or candidate.area<1e-8:return original.tolist()
            return out
        p=Polygon(ring(pg.exterior.coords),[ring(r.coords) for r in pg.interiors if Polygon(r).area>.3])
        if not p.is_valid:p=shapely.make_valid(p)
        parts.extend(polygons(p))
    return unary_union(parts)

def components(xy,r=.55):
    pairs=cKDTree(xy).query_pairs(r,output_type='ndarray')
    graph=coo_matrix((np.ones(len(pairs)),(pairs[:,0],pairs[:,1])),shape=(len(xy),len(xy)))
    return connected_components(graph,directed=False)[1]

def extract_planes(q,n,curv):
    roof=(np.abs(n[:,2])>.50)&(curv<.05)&(q[:,2]>np.quantile(q[:,2],.25))
    ids=np.flatnonzero(roof); rem=ids.copy(); coefs=[]; rng=np.random.default_rng(914)
    minimum=max(20,int(len(ids)*.012)); threshold=.065
    for stage in range(12):
        if len(rem)<minimum:break
        p=q[rem]; best=np.zeros(len(p),bool)
        for _ in range(650):
            tri=p[rng.choice(len(p),3,replace=False)]; a=np.c_[tri[:,:2],np.ones(3)]
            if abs(np.linalg.det(a))<.03:continue
            co=np.linalg.solve(a,tri[:,2])
            if np.linalg.norm(co[:2])>2:continue
            mask=np.abs(p[:,2]-np.c_[p[:,:2],np.ones(len(p))]@co)<threshold
            if mask.sum()>best.sum():best=mask
        if best.sum()<minimum:break
        for _ in range(3):
            co=np.linalg.lstsq(np.c_[p[best,:2],np.ones(best.sum())],p[best,2],rcond=None)[0]
            best=np.abs(p[:,2]-np.c_[p[:,:2],np.ones(len(p))]@co)<threshold
        coefs.append(co);rem=rem[~best]
    if not coefs:raise ValueError('No supported roof plane: sparse/degenerate input or incompatible roof geometry')
    coefs=np.array(coefs)
    residual=np.abs(q[:,2,None]-(q[:,:2]@coefs[:,:2].T+coefs[:,2]))
    labels=residual.argmin(1); labels[residual.min(1)>.10]=-1
    regions=[]; evidence=[]
    for i,co in enumerate(coefs):
        support=q[(labels==i)&roof]
        if len(support)<minimum:continue
        # Use all points close to this plane at its local supported domain.
        near=q[(labels==i)]
        dist=cKDTree(support[:,:2]).query(near[:,:2])[0]
        support=near[dist<.6]
        g=alpha_region(support[:,:2])
        for pg in polygons(g):
            if pg.area<.4 or pg.area/max(pg.length,1)<.15:continue
            pg=ortho_polygon(pg,.16)
            regions.append((co,pg));evidence.append({'kind':'roof_plane','candidate':i,'support_points':len(support),'coefficients':co.tolist()})
    # Sparse roof fixtures are recovered from elevated connected returns even
    # when normal estimation around their edges rejects the top face.
    main=coefs[0]
    # Only use this above-roof supplement for a dominant flat roof.
    if np.linalg.norm(main[:2])<.05:
        elev=q[:,2]-(q[:,:2]@main[:2]+main[2]); ix=np.flatnonzero(elev>.16)
        if len(ix):
            comp=components(q[ix,:2],.5)
            for k in np.unique(comp):
                pts=q[ix[comp==k]]
                if len(pts)<8:continue
                lo,hi=np.quantile(pts[:,:2],[.02,.98],axis=0)
                if np.min(hi-lo)<.12:continue
                if np.max(hi-lo)>3:continue
                top=float(np.quantile(pts[:,2],.85))
                g=box(lo[0],lo[1],hi[0],hi[1]); co=np.array([0.,0.,top])
                regions.append((co,g));evidence.append({'kind':'roof_fixture_inferred_vertical_sides','support_points':len(pts),'coefficients':co.tolist(),'extent_uv':[lo.tolist(),hi.tolist()]})
    # A plane may have disconnected support islands. Keep these as one local
    # domain, rather than competing duplicate roof hypotheses.
    merged=[];meta=[];indices={}
    for (co,domain),ev in zip(regions,evidence):
        key=(ev['kind'],ev.get('candidate',tuple(co)))
        if key in indices:
            j=indices[key];merged[j]=(co,unary_union([merged[j][1],domain]))
        else:
            indices[key]=len(merged);merged.append((co,domain));meta.append(ev)
    return merged,meta,roof,coefs

def wall_lines(q,n,curv):
    out=[]
    walls=(np.abs(n[:,2])<.25)&(curv<.08)
    for axis in [0,1]:
        w=q[walls&(np.abs(n[:,axis])>.9)]
        bins=np.arange(q[:,axis].min()-.1,q[:,axis].max()+.15,.04)
        hist,edges=np.histogram(w[:,axis],bins)
        peaks,_=find_peaks(hist,height=8,distance=5)
        for i in peaks:
            center=(edges[i]+edges[i+1])*.5; pts=w[np.abs(w[:,axis]-center)<.09]
            if len(pts)<15 or np.ptp(pts[:,1-axis])<.6 or np.ptp(pts[:,2])<1:continue
            out.append({'axis':axis,'coord':float(np.median(pts[:,axis])),'range':np.quantile(pts[:,1-axis],[.01,.99]).tolist(),'n':len(pts),'zrange':np.quantile(pts[:,2],[.01,.99]).tolist()})
    # Multiple scan bands on one broad noisy facade are not separate walls.
    # Merge only close parallel detections with strongly overlapping extents.
    merged=[]
    for wall in sorted(out,key=lambda w:(w['axis'],w['coord'])):
        if merged:
            old=merged[-1]
            overlap=min(old['range'][1],wall['range'][1])-max(old['range'][0],wall['range'][0])
            if old['axis']==wall['axis'] and abs(old['coord']-wall['coord'])<.25 and overlap>.75*min(np.ptp(old['range']),np.ptp(wall['range'])):
                axis=wall['axis'];center=(old['coord']+wall['coord'])/2
                w=q[walls&(np.abs(n[:,axis])>.9)&(np.abs(q[:,axis]-center)<.22)]
                old.update(coord=float(np.median(w[:,axis])),n=len(w),range=np.quantile(w[:,1-axis],[.01,.99]).tolist(),zrange=np.quantile(w[:,2],[.01,.99]).tolist(),position_uncertainty=float(np.quantile(np.abs(w[:,axis]-np.median(w[:,axis])),.95)))
                continue
        merged.append(wall.copy())
    return merged

def prepare(input_path):
    input_path=Path(input_path).resolve();number=input_path.stem
    p=np.loadtxt(input_path,ndmin=2)
    if p.shape[1]!=3 or len(p)<20 or not np.isfinite(p).all():
        raise ValueError('Input must contain at least 20 finite XYZ rows and exactly three columns')
    if min(np.ptp(p,axis=0)[:2])<1e-4:
        raise ValueError('Degenerate XY extent: a building footprint cannot be inferred')
    rect=np.array(MultiPoint(p[:,:2]).minimum_rotated_rectangle.exterior.coords)[:-1]
    u=rect[1]-rect[0];u/=np.linalg.norm(u);basis=np.array([u,[-u[1],u[0]]]).T
    q=np.c_[p[:,:2]@basis,p[:,2]];n,curv=normals(q,16)
    regions,evidence,roof,coefs=extract_planes(q,n,curv)
    walls=wall_lines(q,n,curv)
    roofpoints=q[roof]
    # Union of plane footprints preserves reentrant corners; tiny floating
    # fixture tops don't change the exterior footprint.
    footprint=ortho_polygon(alpha_region(q[:,:2],.60),.20)
    parts=polygons(footprint)
    if not parts:raise ValueError('No nondegenerate footprint component')
    discarded_area=0.
    # Fit supported facade coordinates; use the point outline on unseen sides.
    fitted=[]
    for part in parts:
        xy=np.array(part.exterior.coords)[:-1]
        for i in range(len(xy)):
            j=(i+1)%len(xy);delta=xy[j]-xy[i];axis=int(abs(delta[0])>abs(delta[1]))
            if abs(delta[axis])>.2:continue
            center=(xy[i,axis]+xy[j,axis])/2
            candidates=[w for w in walls if w['axis']==axis and abs(w['coord']-center)<.25 and min(max(xy[i,1-axis],xy[j,1-axis]),w['range'][1])-max(min(xy[i,1-axis],xy[j,1-axis]),w['range'][0])>.4]
            if candidates:
                w=max(candidates,key=lambda w:w['n']);xy[i,axis]=xy[j,axis]=w['coord']
        fp=Polygon(xy,[r.coords for r in part.interiors]);fitted.append(fp if fp.is_valid else part)
    footprint=unary_union(fitted)
    print(number,'planes',[(e['kind'],e['support_points'],e['coefficients']) for e in evidence],flush=True)
    return dict(id=number,source=str(input_path),p=p,q=q,basis=basis,n=n,curv=curv,roof=roof,regions=regions,evidence=evidence,footprint=footprint,walls=walls,discarded_footprint_area=discarded_area)

def partition_roof(d):
    fp=shapely.set_precision(d['footprint'],1e-4);d['footprint']=fp;regions=d['regions'];ev=d['evidence'];q=d['q']
    if not regions:raise ValueError('Roof planes have no sufficiently supported local domains')
    coefs=np.array([r[0] for r in regions]);main=[i for i,e in enumerate(ev) if e['kind']=='roof_plane']
    lines=[fp.boundary]
    minx,miny,maxx,maxy=fp.bounds;span=max(maxx-minx,maxy-miny)*3
    # Parallel roof planes at different heights require LOCAL domains. Infer
    # their separation from adjacent support extents, aided by facade setbacks.
    seams=[]
    for i,j in itertools.combinations(main,2):
        diff=coefs[i]-coefs[j]
        if np.linalg.norm(diff[:2])>=.08 or abs(diff[2])<.15:continue
        ci=np.array(regions[i][1].centroid.coords[0]);cj=np.array(regions[j][1].centroid.coords[0]);axis=int(np.argmax(np.abs(cj-ci)))
        left,right=(i,j) if ci[axis]<cj[axis] else (j,i)
        bounds_left=regions[left][1].bounds;bounds_right=regions[right][1].bounds
        coord=(bounds_left[axis+2]+bounds_right[axis])/2
        wall=[w for w in d['walls'] if w['axis']==axis and abs(w['coord']-coord)<.35]
        if wall:coord=min(wall,key=lambda w:abs(w['coord']-coord))['coord']
        line=LineString([(coord,miny-span),(coord,maxy+span)]) if axis==0 else LineString([(minx-span,coord),(maxx+span,coord)])
        lines.append(line.intersection(fp));seams.append((left,right,axis,coord))
        # Parallel planes can represent stepped wings, not just two halves.
        # Local support boundaries let a wing end without deleting another roof.
        if len(main)>2:
            for k in (i,j):
                lines.append(regions[k][1].simplify(.20,preserve_topology=True).boundary.intersection(fp))
    # Exact plane intersections make shared ridges, instead of height mismatch.
    for i,j in itertools.combinations(main,2):
        co=coefs[i]-coefs[j];length=np.linalg.norm(co[:2])
        if length<.08:continue
        normal=co[:2]/length;center=-co[2]/length*normal;tangent=np.array([-normal[1],normal[0]])
        line=LineString([center-tangent*span,center+tangent*span]).intersection(fp)
        if not line.is_empty:lines.append(line)
    for i,e in enumerate(ev):
        if e['kind']!='roof_plane':lines.append(regions[i][1].intersection(fp).boundary)
    network=unary_union([shapely.set_precision(line,1e-4) for line in lines])
    cells=[p for p in polygonize(network) if fp.covers(p.representative_point()) and p.area>1e-9]
    # Local roof-point votes, not global min-envelope, choose each cell's plane.
    candidates=q[d['roof']];res=np.abs(candidates[:,2,None]-(candidates[:,:2]@coefs[main,:2].T+coefs[main,2]))
    good=res.min(1)<.1;labels=np.array(main)[res.argmin(1)[good]];samples=candidates[good,:2];tree=cKDTree(samples)
    if not len(samples):raise ValueError('No local roof observations for domain assignment')
    grouped={i:[] for i in range(len(regions))}
    for cell in cells:
        pt=cell.representative_point();center=np.array([pt.x,pt.y])
        # Vote from observations INSIDE the cell where possible; extrapolation
        # uses nearby roof returns, never a global lowest-plane envelope.
        inside=shapely.contains_xy(cell,samples[:,0],samples[:,1])
        local=np.flatnonzero(inside)
        if len(local)>=3:
            votes=np.bincount(labels[local],minlength=len(regions)).astype(float)
        else:
            dist,near=tree.query(center,k=min(24,len(samples)))
            votes=np.bincount(labels[np.atleast_1d(near)],weights=1/np.maximum(np.atleast_1d(dist),.10)**2,minlength=len(regions))
        winner=max(main,key=lambda i:(votes[i],-regions[i][1].distance(pt)))
        for i,e in enumerate(ev):
            if e['kind']!='roof_plane' and regions[i][1].covers(pt):winner=i
        grouped[winner].append(cell)
    patches=[]
    for i,cells in grouped.items():
        if not cells:continue
        for pg in polygons(unary_union(cells)):
            if pg.area>1e-9:patches.append((i,orient(pg,sign=1)))
    return patches,coefs

def make_mesh(d):
    patches,coefs=partition_roof(d);fp=d['footprint'];base=float(d.get('ground_z',np.quantile(d['q'][:,2],.001)))
    # Split every patch boundary at all XY vertices so T-junctions are explicit.
    xylist=[p for part in polygons(fp) for ring in [part.exterior,*part.interiors] for p in ring.coords[:-1]]
    for _,pg in patches:
        for ring in [pg.exterior,*pg.interiors]:xylist.extend(ring.coords[:-1])
    xyunique=np.unique(np.round(xylist,7),axis=0)
    def split_ring(coords):
        points=np.array(coords);result=[]
        for a,b in zip(points[:-1],points[1:]):
            delta=b-a;ls=np.dot(delta,delta)
            if ls<1e-14:continue
            t=(xyunique-a)@delta/ls;proj=a+t[:,None]*delta
            mask=(t>=-1e-7)&(t<1-1e-7)&(np.linalg.norm(xyunique-proj,axis=1)<2e-6)
            candidates=xyunique[mask][np.argsort(t[mask])]
            result.append(a.tolist())
            result.extend([v.tolist() for v in candidates if np.linalg.norm(v-a)>2e-6])
        return result
    verts=[];faces=[];semantics=[];patch_ids=[];lookup={}
    def vertex(pt):
        # Plane intersections projected to a precision grid may differ by a
        # few microunits in Z. Weld these numerical copies before edge splitting.
        key=tuple(np.round(pt[:2],5))
        for i in lookup.get(key,[]):
            if np.linalg.norm(np.array(verts[i])-pt)<1e-3:return i
        i=len(verts);verts.append(list(map(float,pt)));lookup.setdefault(key,[]).append(i)
        return i
    def addface(points,sem,pi=-1):
        ids=[vertex(p) for p in points];ids=[a for j,a in enumerate(ids) if j==0 or ids[j-1]!=a]
        if len(ids)>2 and ids[0]==ids[-1]:ids.pop()
        if len(set(ids))>=3:faces.append(ids);semantics.append(sem);patch_ids.append(pi)
    def height(i,xy):return float(np.dot(coefs[i,:2],xy)+coefs[i,2])
    edge_map={}
    for i,pg in patches:
        ext=split_ring(pg.exterior.coords);holes=[split_ring(r.coords) for r in pg.interiors]
        holes=[h for h in holes if len(h)>=3 and Polygon(h).area>1e-10]
        if len(ext)<3 or Polygon(ext).area<1e-10:continue
        pg=Polygon(ext,holes)
        for tri in triangulate_polygon(pg):
            tri=orient(tri,sign=1);xy=np.array(tri.exterior.coords)[:-1]
            addface([[*p,height(i,p)] for p in xy],'roof_fixture' if d['evidence'][i]['kind']!='roof_plane' else 'roof',i)
        for ring in [ext,*holes]:
            for a,b in zip(ring,ring[1:]+ring[:1]):
                ka=tuple(np.round(a,7));kb=tuple(np.round(b,7));key=tuple(sorted([ka,kb]));edge_map.setdefault(key,[]).append((i,ka,kb))
    for key,uses in edge_map.items():
        i,a,b=uses[0];za,zb=height(i,a),height(i,b)
        if len(uses)==1:
            addface([[*b,zb],[*a,za],[*a,base],[*b,base]],'facade_completed',i)
        elif len(uses)==2:
            j,_,_=uses[1];ja,jb=height(j,a),height(j,b)
            if max(abs(za-ja),abs(zb-jb))<1e-3:continue
            if (za+zb)<(ja+jb):i,j=j,i;za,zb,ja,jb=ja,jb,za,zb;a,b=b,a;za,zb,ja,jb=zb,za,jb,ja
            addface([[*b,zb],[*a,za],[*a,ja],[*b,jb]],'roof_step_or_fixture_side',i)
        else:raise RuntimeError('Invalid planar partition adjacency')
    ground=unary_union([Polygon(split_ring(part.exterior.coords),[split_ring(r.coords) for r in part.interiors]) for part in polygons(fp)])
    for tri in triangulate_polygon(ground):
        xy=list(orient(tri,sign=-1).exterior.coords)[:-1];addface([[*p,base] for p in xy],'ground_assumed')
    # Vertical step junctions can contain multiple heights: split every mesh edge
    # at collinear vertices to ensure a conforming closed shell.
    arr=np.array(verts)
    for idx,face in enumerate(faces):
        expanded=[]
        for ai,bi in zip(face,face[1:]+face[:1]):
            a,b=arr[ai],arr[bi];delta=b-a;ls=np.dot(delta,delta)
            t=(arr-a)@delta/max(ls,1e-18);dist=np.linalg.norm(arr-(a+t[:,None]*delta),axis=1)
            ids=np.flatnonzero((t>=-1e-7)&(t<1-1e-7)&(dist<2e-6))
            expanded.extend(ids[np.argsort(t[ids])].tolist())
        faces[idx]=list(dict.fromkeys(expanded))
    # UV alignment is rigid and reversible; exports retain input XYZ space.
    arr=np.array(verts);arr[:,:2]=arr[:,:2]@d['basis'].T
    model={'id':d['id'],'source':d['source'],'vertices':arr.tolist(),'faces':faces,'semantics':semantics,'patch_ids':patch_ids,
           'metrics':{'provisional_base_z':base,'base_rule':'z quantile 0.001; not verified terrain'},
           'surface_evidence':d['evidence'],'facade_evidence':d['walls'],'footprint_uv':list(max(polygons(fp),key=lambda p:p.area).exterior.coords),'footprints_uv':[{'exterior':list(part.exterior.coords),'holes':[list(r.coords) for r in part.interiors]} for part in polygons(fp)],'uv_basis':d['basis'].tolist(),
           'inference':'Vertical wall continuation at locally observed boundaries; orthogonal corner completion; fitted local roof steps; roof fixture sides inferred. No windows or material details inferred.'}
    return model,patches


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
        f.write('# pointcloud_to_mesh '+VERSION+'; candidate requires geometry validation; coordinates preserved\n')
        for p in model['vertices']:f.write('v '+' '.join(f'{v:.9f}' for v in p)+'\n')
        for face,sem in zip(model['faces'],model['semantics']):f.write('g '+sem+'\n'+'f '+' '.join(str(i+1) for i in face)+'\n')

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
