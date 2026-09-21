"""Freeze the exact historical v0.5.1 Git blob and evaluate only starter78.

The compatibility wrapper only maps the old harness run(num) interface to the
historical reconstruct() interface. No historical algorithm edits are made.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from statistics import mean

REPO = Path(__file__).resolve().parents[3]
COMMIT = '46a2c3e35cc5d0e715b487020f99574225510e5d'
SOURCE = 'releases/v0.5.1-batch02/source/pointcloud_to_mesh.py'
HISTORICAL_SHA256 = 'c8021924dc9649c70e1f60a92ad1efefeab3b5f1e89042487fe870ed141c188a'
MANIFEST = REPO / 'work/experiments/2026-09-21/starter78-feedback-pilot/setup/all78.json'


def digest(value):
    return hashlib.sha256(value).hexdigest()


def summarize(output):
    output = Path(output).resolve()
    results = json.loads((output / 'results.json').read_text(encoding='utf-8'))
    rows = results['samples']
    summary = {'result_path': str(output / 'results.json'),
               'result_sha256': digest((output / 'results.json').read_bytes()),
               'total': len(rows), 'evaluated': sum(r['status'] == 'evaluated' for r in rows),
               'failed': sum(r['status'] != 'evaluated' for r in rows),
               'topology_pass': sum(r.get('topology_pass', False) for r in rows),
               'strata': {}, 'failures': [], 'noise_diagnostics': [],
               'source_sha256': results['source_sha256'],
               'evaluator_sha256': results['evaluator_sha256'],
               'manifest_sha256': results['manifest_sha256'],
               'wall_seconds': results['wall_seconds'],
               'not_official': True, 'all78_development_only': True}
    for name in sorted({r['stratum'] for r in rows}):
        selected = [r for r in rows if r['stratum'] == name]
        success = [r for r in selected if r['status'] == 'evaluated']
        summary['strata'][name] = {
            'total': len(selected), 'evaluated': len(success), 'failed': len(selected) - len(success),
            'topology_pass': sum(r['topology_pass'] for r in success),
            'means_over_successes_only': {key: mean(r[key] for r in success) if success else None
                                        for key in ['CD', 'ECD', 'NC', 'p95']}}
    for row in rows:
        if row['status'] != 'evaluated':
            summary['failures'].append({'id': row['id'], 'stratum': row['stratum'], 'error': row['error']})
        else:
            model = json.loads((output / 'samples' / row['id'] / 'models/input_lod2.json').read_text(encoding='utf-8'))
            noise = model['noise_diagnostics']
            summary['noise_diagnostics'].append({'id': row['id'], **{k: noise[k] for k in
                                                ['mode', 'input_points', 'used_points', 'excluded_points']}})
    target = output.with_name(output.name + '_summary.json')
    with target.open('x', encoding='utf-8') as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps({k: v for k, v in summary.items() if k not in ['failures', 'noise_diagnostics']}, indent=2))
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=REPO / 'work/experiments/2026-09-21/feedback-components-v002/v051_all78')
    args = parser.parse_args()
    output = args.output.resolve()
    frozen = output.with_name(output.name + '_freeze')
    if output.exists() or frozen.exists():
        raise FileExistsError('Preserve old runs: choose a new --output directory')
    raw = subprocess.check_output(['git', 'show', COMMIT + ':' + SOURCE], cwd=REPO)
    release = json.loads((REPO / 'releases/v0.5.1-batch02/manifest.json').read_text(encoding='utf-8'))
    release_hash = next(row['sha256'] for row in release['files'] if row['path'] == 'source/pointcloud_to_mesh.py')
    if digest(raw) != HISTORICAL_SHA256 or release_hash != HISTORICAL_SHA256:
        raise ValueError('Historical blob and release manifest must match the recorded exact bytes')
    spec = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if len(spec['samples']) != 78 or spec['pilot_partition'] != 'all78' or spec['role'] != 'development' or spec.get('stage_locked'):
        raise ValueError('Only the authorized all78 development manifest may run')
    frozen.mkdir(parents=True, exist_ok=False)
    (frozen / 'historical_pointcloud_to_mesh.py').write_bytes(raw)
    payload = base64.b64encode(raw).decode('ascii')
    wrapper = '''"""Interface-only adapter around the exact historical Git source bytes."""
import base64 as _base64
import hashlib as _hashlib
from pathlib import Path as _Path
_RAW = _base64.b64decode(PAYLOAD)
assert _hashlib.sha256(_RAW).hexdigest() == EXPECTED
exec(compile(_RAW, __file__ + ':historical-v0.5.1', 'exec'), globals())
ROOT = _Path('.')
OUT = _Path('.')

def run(num):
    model = reconstruct(ROOT / 'LiDAR_xyz' / (str(num) + '.xyz'),
                        OUT / (str(num) + '_lod2.obj'),
                        ground_z=None, noise_mode='conservative')
    return model, None, None
'''.replace('PAYLOAD', repr(payload)).replace('EXPECTED', repr(HISTORICAL_SHA256))
    wrapper_path = frozen / 'algorithm_wrapper.py'
    wrapper_path.write_text(wrapper, encoding='utf-8', newline='\n')
    root_bytes = (REPO / 'pointcloud_to_mesh.py').read_bytes()
    evidence = {
        'historical_git_commit': COMMIT,
        'historical_git_path': SOURCE,
        'historical_source_url': 'https://github.com/VISjudy/buildingworld-xyz-to-mesh/blob/' + COMMIT + '/' + SOURCE,
        'historical_source_sha256': digest(raw),
        'historical_release_manifest_sha256': digest((REPO / 'releases/v0.5.1-batch02/manifest.json').read_bytes()),
        'manifest_recorded_source_sha256': release_hash,
        'release_checkout_matches_git_blob': (REPO / SOURCE).read_bytes() == raw,
        'root_source_sha256': digest(root_bytes),
        'root_matches_historical_bytes': root_bytes == raw,
        'root_matches_historical_after_crlf_normalization': root_bytes.replace(b'\r\n', b'\n') == raw.replace(b'\r\n', b'\n'),
        'wrapper_sha256': digest(wrapper_path.read_bytes()),
        'wrapper_scope': 'Only run(num) input/output path and return tuple compatibility; exact source bytes compiled without editing',
        'ground_z': None,
        'noise_mode': 'conservative',
        'noise_processing': 'Historical default isolated-point removal inside algorithm, unchanged; evaluation uses all original canonical input points',
        'coordinate_scope': 'Same input-only canonical bbox diagonal 30 as other starter78 runs; historical near-meter absolute thresholds remain unchanged',
        'input_manifest': str(MANIFEST),
        'input_manifest_sha256': digest(MANIFEST.read_bytes()),
        'sample_count': len(spec['samples']),
        'workers': 2,
        'per_sample_timeout_seconds': 180,
        'python': sys.executable,
        'not_official': True,
        'full_train_or_test_used': False,
    }
    (frozen / 'provenance.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    with (frozen / 'requirements-lock.txt').open('x', encoding='utf-8') as handle:
        subprocess.run([sys.executable, '-m', 'pip', 'freeze'], stdout=handle, check=True)
    subprocess.run([sys.executable, '-B', str(REPO / 'scripts/buildingworld/run_starter78_pilot.py'), 'run',
                    '--source', str(wrapper_path), '--manifest', str(MANIFEST),
                    '--output', str(output), '--workers', '2', '--timeout', '180'], cwd=REPO, check=True)
    summarize(output)


if __name__ == '__main__':
    main()
