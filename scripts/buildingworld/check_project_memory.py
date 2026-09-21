"""Validate project memory routing, evidence paths and append-only record schema."""
import argparse
import json
from pathlib import Path


def validate(root):
    root=Path(root).resolve();errors=[]
    required=['memory.md','AGENTS.md','PROJECT_MEMORY.md','prompt/INDEX.md',
              'prompt/registers/research.md','prompt/registers/datasets.md',
              'prompt/protocols/memory-management.md','prompt/knowledge/experience-index.md',
              'prompt/knowledge/experiences.jsonl','experiments/INDEX.md']
    for name in required:
        if not (root/name).is_file():errors.append('missing: '+name)
    if errors:return errors
    if len((root/'memory.md').read_text(encoding='utf-8').splitlines())>80:errors.append('L1 exceeds 80 lines')
    if 'memory.md' not in (root/'AGENTS.md').read_text(encoding='utf-8'):errors.append('AGENTS missing entry point')
    seen=set()
    for number,line in enumerate((root/'prompt/knowledge/experiences.jsonl').read_text(encoding='utf-8').splitlines(),1):
        if not line.strip():continue
        try:
            row=json.loads(line)
            for field in ['id','date','kind','status','claim','conditions','evidence','counterexamples','next_action']:
                if field not in row:raise ValueError('missing '+field)
            if row['id'] in seen:raise ValueError('duplicate ID')
            seen.add(row['id'])
            if row['status'] not in ['validated_engineering','hypothesis','limitation','correction']:raise ValueError('unknown status')
            if not row['evidence']:raise ValueError('no evidence')
            for name in row['evidence']:
                p=(root/name).resolve()
                if not p.is_relative_to(root) or not p.is_file():raise ValueError('missing/outside evidence: '+name)
        except (ValueError,KeyError,TypeError) as exc:errors.append(f'line {number}: {exc}')
    return errors


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default=str(Path(__file__).resolve().parents[2]))
    errors=validate(parser.parse_args().root)
    print(json.dumps({'valid':not errors,'errors':errors},ensure_ascii=False,indent=2))
    raise SystemExit(bool(errors))
