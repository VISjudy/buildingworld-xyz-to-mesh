"""Create a new standardized version; immutable existing datasets remain untouched."""
import argparse
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.io import read_json, read_points, read_obj, write_obj, write_json, sha256
from harness.preprocess import canonical_transform, normalize, restore


def export(collection, protocol, output):
    collection, out = Path(collection), Path(output).resolve()
    rules = read_json(protocol)
    spec = read_json(collection / 'manifest.json')
    dev = read_json(collection / 'manifests/starter78_development.json')
    active = {r['id'] for r in dev['samples']}
    out.mkdir(parents=True, exist_ok=False)
    records = []
    for row in spec['samples']:
        if sha256(row['points']) != row['point_sha256'] or sha256(row['gt_mesh']) != row['mesh_sha256']:
            raise ValueError('Frozen source hash mismatch')
        p, mesh = read_points(row['points']), read_obj(row['gt_mesh'])
        origin, scale = canonical_transform(p, rules['preprocessing']['target_diagonal'])
        d = out / 'pairs' / row['evaluation_stratum'] / row['id']
        d.mkdir(parents=True)
        np.savetxt(d / 'points.xyz', normalize(p, origin, scale), fmt='%.17g')
        write_obj(d / 'gt.obj', normalize(mesh['vertices'], origin, scale), mesh['faces'], mesh['groups'])
        wire = read_obj(row['gt_wireframe'])
        with (d / 'wireframe.obj').open('x', encoding='utf-8') as f:
            for v in normalize(wire['vertices'], origin, scale):
                f.write('v ' + ' '.join(format(float(x), '.17g') for x in v) + '\n')
            for a, b in wire['lines']:
                f.write(f'l {a+1} {b+1}\n')
        point_error = float(np.abs(restore(read_points(d / 'points.xyz'), origin, scale) - p).max())
        mesh_error = float(np.abs(restore(read_obj(d / 'gt.obj')['vertices'], origin, scale) - mesh['vertices']).max())
        wire_error = float(np.abs(restore(read_obj(d / 'wireframe.obj')['vertices'], origin, scale) - wire['vertices']).max())
        if point_error > 1e-8 or max(mesh_error, wire_error) > 1e-5:
            raise ValueError('Source coordinate roundtrip failed')
        write_json(d / 'transform.json', {'origin': origin.tolist(), 'scale': scale,
            'derived_from': 'input_points_only', 'source_points': row['points'], 'source_mesh': row['gt_mesh'],
            'source_wireframe': row['gt_wireframe'], 'source_points_sha256': row['point_sha256'],
            'source_mesh_sha256': row['mesh_sha256'], 'source_wireframe_sha256': sha256(row['gt_wireframe']),
            'point_count': len(p), 'point_roundtrip_error': point_error, 'mesh_roundtrip_error': mesh_error,
            'wireframe_roundtrip_error': wire_error, 'source_coordinate_frame': row['coordinate_frame'],
            'protocol_sha256': sha256(protocol), 'gt_used_to_define_transform': False})
        records.append({**row, 'points': str(d / 'points.xyz'), 'gt_mesh': str(d / 'gt.obj'),
            'gt_wireframe': str(d / 'wireframe.obj'), 'transform': str(d / 'transform.json'),
            'point_sha256': sha256(d / 'points.xyz'), 'sha256': sha256(d / 'points.xyz'),
            'mesh_sha256': sha256(d / 'gt.obj'), 'source_point_sha256': row['point_sha256'],
            'source_mesh_sha256': row['mesh_sha256'], 'localize': False,
            'coordinate_frame': 'canonical input-bbox diagonal=30 analysis units, not metres',
            'point_count': len(p)})
    for name in ['starter78', 'all_train', 'all_test']:
        chosen = [r for r in records if r['id'] in active] if name == 'starter78' else [r for r in records if r['project_split'] == name[4:]]
        write_json(out / 'manifests' / (name + '.json'), {
            'role': 'development' if name == 'starter78' else ('sealed_test' if name == 'all_test' else 'deferred_train'),
            'stage_locked': name != 'starter78', 'reconstruction_testing_authorized_now': name == 'starter78',
            'protocol_sha256': sha256(protocol), 'samples': chosen})
    write_json(out / 'manifest.json', {'role': 'standardized_inventory', 'stage_locked': True,
                                      'source_manifest_sha256': sha256(collection / 'manifest.json'), 'samples': records})
    write_json(out / 'protocol.json', rules)
    write_json(out / 'verification.json', {'pairs': len(records), 'starter_count': len(active),
               'all_roundtrips_passed': True, 'point_order_preserved': True, 'no_filtering': True,
               'gt_defines_transform': False, 'source_datasets_modified': False,
               'source_collection_manifest_sha256': sha256(collection / 'manifest.json')})
    print('standardized', len(records), 'pairs; active', len(active), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ['collection', 'protocol', 'output']:
        p.add_argument('--' + name, required=True)
    export(**vars(p.parse_args()))
