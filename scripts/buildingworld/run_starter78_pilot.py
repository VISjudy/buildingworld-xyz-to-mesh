"""Frozen, timeout-bounded pilot batches. Does not open the full collection test set."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.io import read_json, write_json, sha256

REPO = Path(__file__).resolve().parents[2]


def setup(manifest, output):
    spec = read_json(manifest)
    if spec['role'] != 'development' or spec.get('stage_locked') or len(spec['samples']) != 78:
        raise ValueError('Only the authorized 78-pair development set may enter this pilot')
    out = Path(output).resolve(); out.mkdir(parents=True, exist_ok=False)
    groups = {'discovery': [], 'selection': [], 'transfer': []}
    for source in ['real_zurich', 'synthetic_mini']:
        rows = sorted([r for r in spec['samples'] if r['evaluation_stratum'] == source],
                      key=lambda r: hashlib.sha256(('pilot78-v1:' + r['id']).encode()).hexdigest())
        for name, subset in [('discovery', rows[:12]), ('selection', rows[12:24]), ('transfer', rows[24:])]:
            groups[name].extend(subset)
    for name, rows in {**groups, 'all78': spec['samples']}.items():
        write_json(out / (name + '.json'), {**spec, 'samples': rows, 'pilot_partition': name})
    write_json(out / 'preregistration.json', {
        'id': 'starter78-feedback-transfer-pilot-v001', 'source_manifest_sha256': sha256(manifest),
        'partition_counts': {k: len(v) for k, v in groups.items()},
        'budget': 'one proposal per independent model condition; one fixed seed; feasibility pilot, not full matrix',
        'feedback_conditions': ['F0 no reconstruction outcome', 'F3 external localized geometric/GT feedback'],
        'knowledge': 'same fixed rules in both groups; feedback is the manipulated factor',
        'discovery': 'Only discovery outcomes are sent to proposal agents',
        'selection': 'Evaluate frozen candidates independently; do not feed scores back during the first round',
        'transfer': 'Compare original/evolved improvement policies restarted from the exact same initial algorithm; summarize policy on discovery/selection only',
        'primary': 'Per-source paired CD/ECD/NC, failures and topology; report all failures, no official score',
        'acceptance': 'No increased failure count or topology failures in either source, mean CD and ECD non-increasing per source, at least one strict decrease; descriptive pilot only',
        'limitations': 'One candidate per arm and one seed cannot establish general LLM feedback efficacy or recursive self-improvement. Model snapshot and token budgets depend on runtime observability.',
        'complete_train_and_test': 'remain stage-locked; not used for inference or feedback'})
    print('pilot partitions:', {k: len(v) for k, v in groups.items()}, flush=True)


def run(source, manifest, output, workers=3, timeout=180):
    spec = read_json(manifest)
    if spec['role'] != 'development' or spec.get('stage_locked') or spec.get('reconstruction_testing_authorized_now') is False:
        raise ValueError('Only active development manifests allowed')
    out = Path(output).resolve(); out.mkdir(parents=True, exist_ok=False)
    frozen = out / 'source'; frozen.mkdir()
    shutil.copyfile(source, frozen / 'algorithm.py')
    shutil.copytree(REPO / 'harness', frozen / 'harness', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    write_json(out / 'inputs.json', spec)
    env = {**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'PYTHONUTF8': '1'}
    start = time.monotonic()

    def one(sample):
        task = out / 'tasks' / (sample['id'] + '.json')
        write_json(task, {'sample': sample, 'source': str(frozen / 'algorithm.py'),
                          'output': str(out / 'samples' / sample['id'])})
        began = time.monotonic()
        try:
            p = subprocess.run([sys.executable, '-B', '-m', 'harness.pilot_worker', '--task', str(task)],
                               cwd=frozen, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
            if p.returncode:
                raise RuntimeError(p.stderr[-3000:])
            row = read_json(out / 'samples' / sample['id'] / 'result.json')
        except Exception as exc:
            row = {'id': sample['id'], 'stratum': sample['evaluation_stratum'], 'status': 'failed',
                   'error': str(exc), 'input_sha256': sample['sha256'], 'seconds': time.monotonic() - began}
        write_json(out / 'progress' / (sample['id'] + '.json'), row)
        return row

    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(one, s) for s in spec['samples']]):
            r = future.result(); results.append(r)
            print(len(results), '/', len(spec['samples']), r['id'], r['status'], flush=True)
    write_json(out / 'results.json', {'samples': sorted(results, key=lambda r: r['id']),
               'source_sha256': sha256(frozen / 'algorithm.py'), 'manifest_sha256': sha256(manifest),
               'evaluator_sha256': sha256(frozen / 'harness/evaluate.py'), 'wall_seconds': time.monotonic() - start,
               'workers': workers, 'per_sample_timeout_seconds': timeout, 'not_official': True,
               'independent_test': False})


if __name__ == '__main__':
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('setup'); q.add_argument('--manifest', required=True); q.add_argument('--output', required=True)
    q = sub.add_parser('run')
    for name in ['source', 'manifest', 'output']:
        q.add_argument('--' + name, required=True)
    q.add_argument('--workers', type=int, default=3); q.add_argument('--timeout', type=int, default=180)
    args = vars(p.parse_args()); command = args.pop('command'); {'setup': setup, 'run': run}[command](**args)
