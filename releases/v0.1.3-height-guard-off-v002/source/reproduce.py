"""Replay this release with its frozen evaluator; no sealed samples allowed."""
import argparse, json, os, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--only');p.add_argument('--timeout',type=int,default=180)
a=p.parse_args();spec=json.loads((root.parent/'reports/inputs.json').read_text(encoding='utf-8'))
assert spec['role']=='development' and not spec.get('stage_locked')
out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
rows=[s for s in spec['samples'] if not a.only or s['id']==a.only]
assert rows, 'No matching samples'
results=[]
env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONUTF8':'1'}
for sample in rows:
    task=out/(sample['id']+'.task.json')
    task.write_text(json.dumps({'sample':sample,'source':str(root/'algorithm.py'),'output':str(out/'samples'/sample['id'])}),encoding='utf-8')
    try:
        r=subprocess.run([sys.executable,'-B','-m','harness.pilot_worker','--task',str(task)],cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=a.timeout)
        if r.returncode: raise RuntimeError(r.stderr)
        result=json.loads((out/'samples'/sample['id']/'result.json').read_text(encoding='utf-8'))
    except Exception as exc:result={'id':sample['id'],'status':'failed','error':str(exc)}
    results.append(result)
(out/'results.json').write_text(json.dumps({'samples':results},indent=2),encoding='utf-8')
