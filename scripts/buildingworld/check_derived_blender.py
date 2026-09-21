"""Independent, local-coordinate topology/BVH checks of derived meshes."""
import argparse,json,sys,hashlib
from pathlib import Path
import bpy,bmesh
from mathutils.bvhtree import BVHTree
from mathutils import Vector


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dataset',required=True);ap.add_argument('--output',required=True)
    a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);root=Path(a.dataset)
    if Path(a.output).exists():raise FileExistsError(a.output)
    rows=[]
    for p in sorted(root.glob('*/completed_hypothesis.obj')):
        vertices=[];faces=[]
        for raw in p.read_text().splitlines():
            t=raw.split()
            if not t:continue
            if t[0]=='v':vertices.append(Vector(tuple(map(float,t[1:4]))))
            elif t[0]=='f':faces.append([int(x)-1 for x in t[1:]])
        center=sum(vertices,Vector())/len(vertices);vertices=[v-center for v in vertices]
        mesh=bpy.data.meshes.new(p.parent.name);mesh.from_pydata(vertices,[],faces);mesh.update();mesh.calc_loop_triangles()
        bm=bmesh.new();bm.from_mesh(mesh)
        tris=[tuple(t.vertices) for t in mesh.loop_triangles]
        tree=BVHTree.FromPolygons(vertices,tris,all_triangles=True,epsilon=1e-8)
        overlap=sorted({tuple(sorted((i,j))) for i,j in tree.overlap(tree) if i!=j and not set(tris[i])&set(tris[j])})
        boundary=sum(e.is_boundary for e in bm.edges);nonmanifold=sum(not e.is_manifold and not e.is_boundary for e in bm.edges)
        winding=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
        volume=bm.calc_volume(signed=True);degenerate=sum(f.calc_area()<=1e-10 for f in bm.faces)
        eligible=boundary==nonmanifold==winding==degenerate==0 and volume>0 and len(overlap)==0
        rows.append({'id':p.parent.name,'mesh_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
          'boundary_edges':boundary,'nonmanifold_edges':nonmanifold,'winding_edges':winding,'degenerate_faces':degenerate,
          'signed_volume':volume,'nonadjacent_bvh_overlap_candidates':len(overlap),'overlap_pairs':overlap[:100],
          'provisional_training_eligible':eligible,'official_gt':False,
          'limitations':'BVH checks nonadjacent triangles; shared-vertex self intersections and semantic correctness remain unproven'})
        bm.free()
    Path(a.output).write_text(json.dumps({'blender':bpy.app.version_string,'samples':rows,
       'eligible':sum(r['provisional_training_eligible'] for r in rows),'status':'provisional_derived_supervision_not_official_GT'},indent=2),encoding='utf-8')


if __name__=='__main__':main()
