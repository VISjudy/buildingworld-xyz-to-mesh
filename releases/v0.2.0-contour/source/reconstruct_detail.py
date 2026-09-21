"""Evidence-constrained piecewise roof/vertical-facade reconstruction.

No learned model, ground truth, or claimed recovery of unobserved windows.
Local plane domains preserve reentrant corners, height steps and roof fixtures.
"""
from pathlib import Path
import sys,os,json,itertools
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'deps')); os.environ['MPLCONFIGDIR']=str(HERE/'mplconfig')
import numpy as np
from scipy.spatial import cKDTree,Delaunay
from scipy.signal import find_peaks
from scipy.sparse.csgraph import connected_components
from scipy.sparse import coo_matrix
from shapely.geometry import MultiPoint,Polygon,LineString,Point,box
from shapely.ops import unary_union,polygonize,split
from shapely.geometry.polygon import orient
import shapely
from reconstruct_baseline import normals
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
ROOT=HERE.parents[1]; OUT=ROOT/'output/lod2_xyz_detail'; OUT.mkdir(parents=True,exist_ok=True)

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
            xy=np.array(coords)[:-1]; dirs=np.roll(xy,-1,axis=0)-xy
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
    return regions,evidence,roof,coefs

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

def prepare(number):
    p=np.loadtxt(ROOT/'LiDAR_xyz'/f'{number}.xyz'); rect=np.array(MultiPoint(p[:,:2]).minimum_rotated_rectangle.exterior.coords)[:-1]
    u=rect[1]-rect[0];u/=np.linalg.norm(u);basis=np.array([u,[-u[1],u[0]]]).T
    q=np.c_[p[:,:2]@basis,p[:,2]];n,curv=normals(q,16)
    regions,evidence,roof,coefs=extract_planes(q,n,curv)
    walls=wall_lines(q,n,curv)
    roofpoints=q[roof]
    # Union of plane footprints preserves reentrant corners; tiny floating
    # fixture tops don't change the exterior footprint.
    footprint=ortho_polygon(alpha_region(q[:,:2],.60),.20)
    footprint=max(polygons(footprint),key=lambda g:g.area)
    # Fit supported facade coordinates; use the point outline on unseen sides.
    xy=np.array(footprint.exterior.coords)[:-1]
    for i in range(len(xy)):
        j=(i+1)%len(xy);delta=xy[j]-xy[i];axis=int(abs(delta[0])>abs(delta[1]))
        if abs(delta[axis])>.2:continue
        center=(xy[i,axis]+xy[j,axis])/2
        candidates=[w for w in walls if w['axis']==axis and abs(w['coord']-center)<.25 and min(max(xy[i,1-axis],xy[j,1-axis]),w['range'][1])-max(min(xy[i,1-axis],xy[j,1-axis]),w['range'][0])>.4]
        if candidates:
            w=max(candidates,key=lambda w:w['n']);xy[i,axis]=xy[j,axis]=w['coord']
    fp=Polygon(xy)
    if fp.is_valid:footprint=fp
    print(number,'planes',[(e['kind'],e['support_points'],e['coefficients']) for e in evidence],flush=True)
    return dict(id=number,p=p,q=q,basis=basis,n=n,curv=curv,roof=roof,regions=regions,evidence=evidence,footprint=footprint,walls=walls)

def partition_roof(d):
    fp=shapely.set_precision(d['footprint'],1e-6);d['footprint']=fp;regions=d['regions'];ev=d['evidence'];q=d['q']
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
    # Exact plane intersections make shared ridges, instead of height mismatch.
    for i,j in itertools.combinations(main,2):
        co=coefs[i]-coefs[j];length=np.linalg.norm(co[:2])
        if length<.08:continue
        normal=co[:2]/length;center=-co[2]/length*normal;tangent=np.array([-normal[1],normal[0]])
        line=LineString([center-tangent*span,center+tangent*span]).intersection(fp)
        if not line.is_empty:lines.append(line)
    for i,e in enumerate(ev):
        if e['kind']!='roof_plane':lines.append(regions[i][1].intersection(fp).boundary)
    network=unary_union([shapely.set_precision(line,1e-6) for line in lines])
    cells=[p for p in polygonize(network) if fp.covers(p.representative_point()) and p.area>1e-9]
    # Local roof-point votes, not global min-envelope, choose each cell's plane.
    candidates=q[d['roof']];res=np.abs(candidates[:,2,None]-(candidates[:,:2]@coefs[main,:2].T+coefs[main,2]))
    good=res.min(1)<.1;labels=np.array(main)[res.argmin(1)[good]];samples=candidates[good,:2];tree=cKDTree(samples)
    grouped={i:[] for i in range(len(regions))}
    for cell in cells:
        pt=cell.representative_point();center=np.array([pt.x,pt.y])
        available=set(main)
        for left,right,axis,coord in seams:
            available.discard(right if center[axis]<coord else left)
        # The remaining opposing roof facets meet at their actual intersection.
        options=sorted(available);winner=min(options,key=lambda i:float(center@coefs[i,:2]+coefs[i,2]))
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
    patches,coefs=partition_roof(d);fp=d['footprint'];base=float(np.quantile(d['q'][:,2],.001))
    # Split every patch boundary at all XY vertices so T-junctions are explicit.
    xylist=list(fp.exterior.coords[:-1])
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
        key=tuple(np.round(pt,6))
        if key not in lookup:lookup[key]=len(verts);verts.append(list(map(float,pt)))
        return lookup[key]
    def addface(points,sem,pi=-1):
        ids=[vertex(p) for p in points];ids=[a for j,a in enumerate(ids) if j==0 or ids[j-1]!=a]
        if len(ids)>2 and ids[0]==ids[-1]:ids.pop()
        if len(set(ids))>=3:faces.append(ids);semantics.append(sem);patch_ids.append(pi)
    def height(i,xy):return float(np.dot(coefs[i,:2],xy)+coefs[i,2])
    edge_map={}
    for i,pg in patches:
        ext=split_ring(pg.exterior.coords);holes=[split_ring(r.coords) for r in pg.interiors]
        pg=Polygon(ext,holes)
        for tri in shapely.constrained_delaunay_triangles(pg).geoms:
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
            if max(abs(za-ja),abs(zb-jb))<1e-5:continue
            if (za+zb)<(ja+jb):i,j=j,i;za,zb,ja,jb=ja,jb,za,zb;a,b=b,a;za,zb,ja,jb=zb,za,jb,ja
            addface([[*b,zb],[*a,za],[*a,ja],[*b,jb]],'roof_step_or_fixture_side',i)
        else:raise RuntimeError('Invalid planar partition adjacency')
    ground=Polygon(split_ring(fp.exterior.coords),[split_ring(r.coords) for r in fp.interiors])
    for tri in shapely.constrained_delaunay_triangles(ground).geoms:
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
    model={'id':d['id'],'source':str(ROOT/'LiDAR_xyz'/f"{d['id']}.xyz"),'vertices':arr.tolist(),'faces':faces,'semantics':semantics,'patch_ids':patch_ids,
           'metrics':{'provisional_base_z':base,'base_rule':'z quantile 0.001; not verified terrain'},
           'surface_evidence':d['evidence'],'facade_evidence':d['walls'],'footprint_uv':list(fp.exterior.coords),'uv_basis':d['basis'].tolist(),
           'inference':'Vertical wall continuation at locally observed boundaries; orthogonal corner completion; fitted local roof steps; roof fixture sides inferred. No windows or material details inferred.'}
    return model,patches

def save_model(model):
    name=model['id'];(OUT/f'{name}_model.json').write_text(json.dumps(model,indent=2),encoding='utf8')
    with (OUT/f'{name}_lod2.obj').open('w',encoding='utf8') as f:
        f.write('# Evidence-constrained XYZ reconstruction; provisional ground.\n')
        for p in model['vertices']:f.write('v '+' '.join(f'{v:.8f}' for v in p)+'\n')
        for face,sem in zip(model['faces'],model['semantics']):f.write('g '+sem+'\n'+'f '+' '.join(str(i+1) for i in face)+'\n')

def mesh_preview(all_data,models):
    fig=plt.figure(figsize=(17,5*len(models)))
    for row,(d,model) in enumerate(zip(all_data,models)):
        p=d['p'];vs=np.array(model['vertices']);old=json.loads((ROOT/'output/lod2_xyz_baseline'/f"{d['id']}_model.json").read_text())
        for col in range(3):
            ax=fig.add_subplot(len(models),3,row*3+col+1,projection='3d')
            if col==0:ax.scatter(p[:,0],p[:,1],p[:,2],c=p[:,2],s=2,cmap='turbo')
            else:
                m=old if col==1 else model;v=np.array(m['vertices']);colors=['#cd764a' if 'roof' in s else '#bacdda' for s in m['semantics']]
                ax.add_collection3d(Poly3DCollection([v[f] for f in m['faces']],facecolors=colors,edgecolors='#50616f',linewidths=.25,alpha=.8))
            ax.set_title(d['id']+' | '+['Input XYZ','Previous rectangle baseline','Revised contour + local roof'][col]);ax.set(xlabel='X',ylabel='Y',zlabel='Z')
            ax.set_xlim(p[:,0].min()-1,p[:,0].max()+1);ax.set_ylim(p[:,1].min()-1,p[:,1].max()+1);ax.set_zlim(p[:,2].min()-1,p[:,2].max()+1);ax.set_box_aspect(np.ptp(p,axis=0));ax.view_init(32,-55)
    fig.tight_layout();fig.savefig(OUT/'before_after.png',dpi=150);plt.close(fig)

def plot_regions(all_data):
    fig,axes=plt.subplots(len(all_data),2,figsize=(14,5*len(all_data)))
    for row,d in enumerate(all_data):
        q=d['q'];ax=axes[row,0];ax.scatter(q[:,0],q[:,1],c=q[:,2],s=4,cmap='turbo');x,y=d['footprint'].exterior.xy;ax.plot(x,y,'k-',lw=2)
        for line in d['walls']:
            if line['axis']==0:ax.plot([line['coord']]*2,line['range'],'m-',lw=2)
            else:ax.plot(line['range'],[line['coord']]*2,'m-',lw=2)
        ax.set_title(d['id']+' | outline + supported facade planes');ax.set_aspect('equal');ax.grid(alpha=.2)
        ax=axes[row,1];ax.scatter(q[:,0],q[:,1],c='lightgrey',s=3)
        for i,((co,region),ev) in enumerate(zip(d['regions'],d['evidence'])):
            for pg in polygons(region):
                x,y=pg.exterior.xy;ax.fill(x,y,alpha=.22);ax.plot(x,y,lw=1);c=pg.representative_point();ax.text(c.x,c.y,str(i),fontsize=12)
        ax.set_title(d['id']+' | locally supported roof patches');ax.set_aspect('equal');ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'surface_evidence.png',dpi=160);plt.close(fig)

if __name__=='__main__':
    data=[prepare(num) for num in ['10','1000','2000']];plot_regions(data)
    models=[]
    for d in data:
        model,patches=make_mesh(d);save_model(model);models.append(model)
        print(d['id'],'mesh',len(model['vertices']),len(model['faces']),'patches',[(i,round(pg.area,3)) for i,pg in patches],flush=True)
    mesh_preview(data,models)
