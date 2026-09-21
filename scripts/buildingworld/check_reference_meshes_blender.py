"""Independent Blender data QA, without loading a scene or changing reference meshes."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def check(row):
    path = Path(row['mesh'])
    vertices, faces = [], []
    for line in path.read_text(encoding='utf-8').splitlines():
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] == 'v':
            vertices.append(Vector(tuple(map(float, tokens[1:4]))))
        elif tokens[0] == 'f':
            indices = [int(t.split('/')[0]) for t in tokens[1:]]
            faces.append([i - 1 if i > 0 else len(vertices) + i for i in indices])
    center = sum(vertices, Vector()) / len(vertices)
    vertices = [v - center for v in vertices]
    mesh = bpy.data.meshes.new('reference-audit')
    bm = bmesh.new()
    try:
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        mesh.calc_loop_triangles()
        bm.from_mesh(mesh)
        tris = [tuple(t.vertices) for t in mesh.loop_triangles]
        tree = BVHTree.FromPolygons(vertices, tris, all_triangles=True, epsilon=1e-8)
        overlaps = sorted({tuple(sorted((i, j))) for i, j in tree.overlap(tree)
                           if i != j and not set(tris[i]) & set(tris[j])})
        boundary = sum(e.is_boundary for e in bm.edges)
        nonmanifold = sum(not e.is_manifold and not e.is_boundary for e in bm.edges)
        winding = sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
        degenerate = sum(f.calc_area() <= 1e-12 for f in bm.faces)
        volume = bm.calc_volume(signed=True)
        return {'id': row['id'], 'city': row['city'], 'split': row['split'],
                'mesh_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'boundary_edges': boundary, 'nonmanifold_edges': nonmanifold,
                'winding_edges': winding, 'degenerate_faces': degenerate,
                'signed_volume': volume, 'nonadjacent_bvh_overlap_candidates': len(overlaps),
                'overlap_pairs': overlaps,
                'pass': boundary == nonmanifold == winding == degenerate == 0
                        and volume > 0 and not overlaps}
    finally:
        bm.free()
        bpy.data.meshes.remove(mesh)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    audit = json.loads(Path(args.audit).read_text(encoding='utf-8'))
    results = []
    for row in audit['results']:
        if not row.get('selected_for_facade_development'):
            continue
        try:
            results.append(check(row))
        except Exception as exc:
            results.append({'id': row['id'], 'city': row['city'], 'split': row['split'],
                            'pass': False, 'error': str(exc)})
    with output.open('x', encoding='utf-8') as stream:
        json.dump({'blender': bpy.app.version_string, 'results': results,
                   'passed': sum(r['pass'] for r in results),
                   'input_audit_sha256': hashlib.sha256(Path(args.audit).read_bytes()).hexdigest(),
                   'limitation': 'Nonadjacent BVH is a conservative candidate screen, not a full solid intersection proof. Shared-vertex intersections and semantic accuracy remain unproven.',
                   'reference_meshes_modified': False}, stream, indent=2)
    print('reference QA:', sum(r['pass'] for r in results), '/', len(results), flush=True)


if __name__ == '__main__':
    main()
