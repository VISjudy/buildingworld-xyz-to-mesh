"""One bounded isolated process: candidate inference, immutable external evaluation."""
import argparse
from pathlib import Path
import time
from .io import read_json, write_json, sha256, read_obj, write_obj
from .adapter import reconstruct
from .evaluate import evaluate, structure_edges
from .preprocess import restore


def work(task_file):
    task = read_json(task_file)
    sample, out = task['sample'], Path(task['output'])
    start = time.monotonic()
    if sha256(sample['points']) != sample['sha256'] or sha256(sample['gt_mesh']) != sample['mesh_sha256']:
        raise ValueError('Input or reference hash mismatch')
    model = reconstruct(task['source'], sample['points'], out, localize=False)
    report = evaluate(model, sample['points'], sample['gt_mesh'], sample['gt_wireframe'], config={
        'unit_status': 'canonical input-only bbox diagonal 30; not metres',
        'coordinate_protocol': 'paired-lod2-data-v001'})
    write_json(out / 'evaluation.json', report)
    obj = read_obj(model)
    transform = read_json(sample['transform'])
    source_v = restore(obj['vertices'], transform['origin'], transform['scale'])
    write_obj(out / 'model_source.obj', source_v, obj['faces'], obj['groups'])
    edges, _ = structure_edges(obj)
    with (out / 'wireframe_source.obj').open('x', encoding='utf-8') as f:
        for v in source_v:
            f.write('v ' + ' '.join(format(float(x), '.17g') for x in v) + '\n')
        for a, b in edges:
            f.write(f'l {a+1} {b+1}\n')
    t, m = report['topology'], report['local_reference']
    result = {'id': sample['id'], 'status': 'evaluated', 'stratum': sample['evaluation_stratum'],
              'seconds': time.monotonic() - start, 'input_sha256': sample['sha256'],
              'mesh_sha256': sha256(model), 'source_mesh_sha256': sha256(out / 'model_source.obj'),
              'CD': m['CD'], 'ECD': m['ECD'], 'NC': m['NC'], 'V_Ratio': m['V_Ratio'], 'F_Ratio': m['F_Ratio'],
              'p95': report['observed']['all_points_to_surface']['p95'],
              'open_edges': len(t['open_edges']), 'nonmanifold_edges': len(t['nonmanifold_edges']),
              'winding_edges': len(t['inconsistent_winding_edges']),
              'topology_pass': t['watertight'] and not t['inconsistent_winding_edges'] and not t['degenerate_triangles'],
              'source_scale': transform['scale'], 'self_intersection': 'not_checked'}
    write_json(out / 'result.json', result)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--task', required=True)
    work(p.parse_args().task)
