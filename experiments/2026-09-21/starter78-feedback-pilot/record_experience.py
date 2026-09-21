"""Append this completed experiment's evidence records once; preserve older history."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[3]
target=root/'prompt/knowledge/experiences.jsonl'
rows=[
 dict(id='EXP-S006',kind='success',status='validated_engineering',
 claim='562 paired samples were standardized with an input-only invertible transform and passed roundtrip checks.',
 conditions='Only affine normalization, unchanged point order/count; neither GT-defined transform nor ground-point injection.',
 evidence=['docs/DATASET_METHODS_V001.md','reports/2026-09-21-starter78-feedback-pilot/summary.json'],
 counterexamples='Bounding-box scale is outlier-sensitive; QA does not establish reconstruction quality.',
 next_action='Keep protocol version fixed and test normalization sensitivity later.'),
 dict(id='EXP-H001',kind='success',status='hypothesis',
 claim='Failure-gated roof recovery recovered six starter buildings while common-success metrics stayed identical; a separate no-feedback footprint proposal improved geometry.',
 conditions='Single proposal and seed; 78 development pairs; source-stratified paired evaluation.',
 evidence=['reports/2026-09-21-starter78-feedback-pilot/summary.json','reports/2026-09-21-starter78-feedback-pilot/F3_proposal.json'],
 counterexamples='One F3 failure remains; no-feedback geometry gains mean the result does not prove F3 universally better.',
 next_action='Separate recovery, geometry and their interaction in repeated controlled proposals.'),
 dict(id='EXP-F002',kind='failure',status='limitation',
 claim='The policy distilled from discovery24 and selection24 did not improve same-start transfer30 outcomes over the original Harness.',
 conditions='Both policies proposed one modification; same initial code and evidence content, inherited model configuration.',
 evidence=['reports/2026-09-21-starter78-feedback-pilot/summary.json','reports/2026-09-21-starter78-feedback-pilot/policy_evolved.json'],
 counterexamples='This single null result does not disprove other policy designs; both candidate activation hypotheses failed to change measured outcomes.',
 next_action='Diagnose candidate support and failed activation directly, then preregister another independent transfer trial.')]
existing={json.loads(line)['id'] for line in target.read_text(encoding='utf-8').splitlines() if line.strip()}
assert not any(r['id'] in existing for r in rows), 'Do not duplicate or overwrite experience'
with target.open('a',encoding='utf-8') as f:
 for r in rows:
  f.write(json.dumps({'date':'2026-09-21',**r},ensure_ascii=False)+'\n')
