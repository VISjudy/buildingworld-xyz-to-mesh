"""Recover planar cycles from wireframe; derived meshes are NEVER official GT."""
from collections import defaultdict
from pathlib import Path
import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union, polygonize
from .io import read_obj, read_points, write_obj, write_json, sha256, triangulate


def derive_wireframe(wireframe, points, output, plane_tolerance=.02, method="projected_cycles"):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    wf = read_obj(wireframe)
    p = read_points(points)
    origin = wf["vertices"].mean(0)
    v = wf["vertices"] - origin
    edges = wf["lines"]
    if not edges:
        raise ValueError("Wireframe has no line elements")
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b); adj[b].add(a)
    candidates = []
    for i, neighbors in adj.items():
        ns = sorted(neighbors)
        for ai, a in enumerate(ns):
            for b in ns[ai+1:]:
                n = np.cross(v[a]-v[i], v[b]-v[i])
                if np.linalg.norm(n) < 1e-8:
                    continue
                n /= np.linalg.norm(n)
                if n[np.argmax(np.abs(n))] < 0:
                    n = -n
                d = float(n @ v[i])
                if not any(abs(d-e) < plane_tolerance and np.dot(n,m) > .9999 for m,e in candidates):
                    candidates.append((n,d))
    vertices, faces, groups, seen = [], [], [], set()
    vertex_index = {}

    def add_vertex(q):
        key = tuple(np.round(q, 7))
        if key not in vertex_index:
            vertex_index[key] = len(vertices); vertices.append(q.tolist())
        return vertex_index[key]

    rejected_ambiguous=0
    if method=="projected_cycles":
        # A roof graph is often only approximately planar. Preserve its original
        # elevations instead of projecting them onto independently fitted planes.
        segments=[(v[a],v[b]) for a,b in edges if np.linalg.norm(v[b,:2]-v[a,:2])>1e-8]
        network=unary_union([LineString([a[:2],b[:2]]) for a,b in segments])
        for poly in polygonize(network):
            if poly.area<1e-6 or poly.interiors:continue
            q3=[];ambiguous=False
            for xy in np.asarray(poly.exterior.coords)[:-1]:
                heights=[]
                for a,b in segments:
                    delta=b[:2]-a[:2];t=float(np.dot(xy-a[:2],delta)/np.dot(delta,delta))
                    if -.00001<=t<=1.00001 and np.linalg.norm(a[:2]+t*delta-xy)<1e-5:
                        heights.append(float(a[2]+t*(b[2]-a[2])))
                if not heights or max(heights)-min(heights)>plane_tolerance:
                    ambiguous=True;break
                q3.append([*xy,float(np.mean(heights))])
            if ambiguous:rejected_ambiguous+=1;continue
            q3=np.asarray(q3)
            expected=np.cross(q3-q3.mean(0),np.roll(q3,-1,axis=0)-q3.mean(0)).sum(0)
            if expected[2]<0:q3=q3[::-1]
            key=tuple(sorted(tuple(np.round(t,5)) for t in q3));seen.add(key)
            faces.append([add_vertex(qi) for qi in q3]);groups.append("wireframe_cycle_interpolated_surface")
    elif method!="planar_cycles":raise ValueError("Unknown derivation method")
    for n, d in (candidates if method=="planar_cycles" else []):
        selected = [(a,b) for a,b in edges if max(abs(n@v[a]-d),abs(n@v[b]-d)) <= plane_tolerance]
        if len(selected) < 3:
            continue
        axis = np.eye(3)[np.argmin(np.abs(n))]
        x = np.cross(axis,n); x /= np.linalg.norm(x); y = np.cross(n,x)
        xy = np.column_stack((v@x, v@y))
        for poly in polygonize(unary_union([LineString(xy[[a,b]]) for a,b in selected])):
            if poly.area < 1e-6 or poly.interiors:
                continue
            q = np.asarray(poly.exterior.coords)[:-1]
            q3 = q[:,0,None]*x + q[:,1,None]*y + d*n
            key = tuple(sorted(tuple(np.round(t,5)) for t in q3))
            if key in seen:
                continue
            seen.add(key)
            # Upward orientation for roofs; vertical orientation remains a hypothesis.
            expected = np.cross(q3-q3.mean(0),np.roll(q3,-1,axis=0)-q3.mean(0)).sum(0)
            if expected[2] < 0:
                q3 = q3[::-1]
            faces.append([add_vertex(qi) for qi in q3])
            groups.append("wireframe_planar_cycle")
    if not faces:
        raise ValueError("No planar closed cycles recovered; do not fabricate a mesh")
    roof = {"vertices":np.asarray(vertices),"faces":[f[:] for f in faces],"groups":groups[:]}
    roof_path = output/"wireframe_surface.obj"
    write_obj(roof_path, roof["vertices"]+origin, faces, groups)
    _, _ = triangulate(roof)
    incidence=defaultdict(list)
    for fi,f in enumerate(faces):
        for a,b in zip(f,f[1:]+f[:1]):
            incidence[tuple(sorted((a,b)))].append((a,b))
    boundaries=[x[0] for x in incidence.values() if len(x)==1]
    base=float(np.quantile(p[:,2],.001)-origin[2])
    bottom={}
    # Every inferred face is separately labeled, including courtyard walls.
    for a,b in boundaries:
        for idx in [a,b]:
            if idx not in bottom:
                q=np.array(vertices[idx]);q[2]=base;bottom[idx]=add_vertex(q)
        if len({a,b,bottom[a],bottom[b]})>=3:
            faces.append([b,a,bottom[a],bottom[b]])
            groups.append("inferred_vertical_wall")
    footprint=unary_union([Polygon(roof["vertices"][f,:2]) for f in roof["faces"][:len(seen)]
                          if Polygon(roof["vertices"][f,:2]).is_valid and Polygon(roof["vertices"][f,:2]).area>1e-8])
    # Triangulate planar footprint polygons with holes using Earcut.
    import mapbox_earcut
    polygons=[footprint] if footprint.geom_type=="Polygon" else list(getattr(footprint,"geoms",[]))
    for poly in polygons:
        if poly.geom_type!="Polygon":continue
        rings=[np.asarray(poly.exterior.coords)[:-1]]+[np.asarray(r.coords)[:-1] for r in poly.interiors]
        xy=np.concatenate(rings); ends=np.cumsum([len(r) for r in rings],dtype=np.uint32)
        tri=mapbox_earcut.triangulate_float64(np.ascontiguousarray(xy),ends).reshape(-1,3)
        for ids in tri:
            q=xy[ids]
            if np.linalg.det(np.stack([q[1]-q[0],q[2]-q[0]]))>0:ids=ids[::-1]
            faces.append([add_vertex(np.array([*xy[i],base])) for i in ids]);groups.append("inferred_base")
    # Conform triangulated faces at every collinear boundary vertex. Earcut can
    # remove collinear vertices, so split the resulting triangles again using an
    # interior centroid. This preserves the wall/base edge segmentation.
    tri_obj={"vertices":np.asarray(vertices),"faces":faces,"groups":groups}
    tri,src=triangulate(tri_obj);new_faces=[];new_groups=[]
    vv=np.asarray(vertices)
    for t,fi in zip(tri,src):
        ring=[]
        for a,b in zip(t,np.roll(t,-1)):
            delta=vv[b]-vv[a];length2=float(delta@delta)
            if length2<1e-18:continue
            tt=(vv-vv[a])@delta/length2
            distance=np.linalg.norm(vv-(vv[a]+tt[:,None]*delta),axis=1)
            inner=np.flatnonzero((tt>1e-7)&(tt<1-1e-7)&(distance<1e-7))
            ring.append(int(a));ring.extend(int(i) for i in inner[np.argsort(tt[inner])])
        if len(ring)<3:continue
        if len(ring)==3:new_faces.append(ring);new_groups.append(groups[fi]);continue
        center=add_vertex(vv[t].mean(0))
        for a,b in zip(ring,ring[1:]+ring[:1]):
            if np.linalg.norm(np.cross(np.array(vertices[a])-vertices[center],np.array(vertices[b])-vertices[center]))>1e-12:
                new_faces.append([a,b,center]);new_groups.append(groups[fi])
    faces,groups=new_faces,new_groups
    completed=output/"completed_hypothesis.obj"
    write_obj(completed,np.asarray(vertices)+origin,faces,groups)
    meta={"status":"derived_unvalidated", "is_official_mesh_gt":False,
          "source_wireframe_sha256":sha256(wireframe),"source_points_sha256":sha256(points),
          "method":method,"ambiguous_cycles_rejected":rejected_ambiguous,
          "plane_tolerance_source_units":plane_tolerance,"candidate_planes":len(candidates),
          "surface_faces":len(seen),"inferred_faces":sum(g.startswith('inferred') for g in groups),
          "base_rule":"point Z quantile .001; NOT terrain truth", "face_provenance":groups,
          "known_limits":["Coplanar cycles may include unintended faces", "Wireframe may describe roofs only",
                          "Inferred walls/base must not be scored as independent ground truth",
                          "Requires geometric and visual QA before supervised training"],
          "mesh_sha256":sha256(completed),"wireframe_surface_sha256":sha256(roof_path)}
    write_json(output/"provenance.json",meta)
    return meta


def derive_dataset(root, output):
    root,output=Path(root),Path(output)
    output.mkdir(parents=True,exist_ok=False)
    pcs={p.stem:p for p in (root/"pointcloud").glob("*.xyz")}
    wires={p.stem:p for p in (root/"wireframe").glob("*.obj")}
    rows=[]
    for bid in sorted(pcs.keys() & wires.keys()):
        try:
            result=derive_wireframe(wires[bid],pcs[bid],output/bid)
            rows.append({"id":bid,**result})
        except Exception as exc:
            rows.append({"id":bid,"status":"failed","error":str(exc)})
    write_json(output/"dataset_manifest.json",{"role":"derived_training_candidates_only","official_gt":False,
        "source_root":str(root.resolve()),"unpaired_points":sorted(pcs.keys()-wires.keys()),
        "unpaired_wires":sorted(wires.keys()-pcs.keys()),"samples":rows})
    return rows
