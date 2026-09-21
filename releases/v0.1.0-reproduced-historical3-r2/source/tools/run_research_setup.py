"""Create local manifests and preserve the exact Git blob of the v0.1.0 algorithm."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from harness.io import sha256,write_json


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--points',required=True);ap.add_argument('--output',required=True)
    args=ap.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    blob=subprocess.check_output(['git','show','46a2c3e35cc5d0e715b487020f99574225510e5d:releases/v0.1.0-baseline/source/reconstruct_baseline.py'],cwd=ROOT)
    (out/'baseline_original.py').write_bytes(blob)
    paths=sorted(Path(args.points).resolve().glob('*.xyz'))
    rng=np.random.default_rng(20260921)
    pool=[p for p in paths if p.stem not in ['10','1000','2000']]
    chosen=[pool[i] for i in sorted(rng.choice(len(pool),20,replace=False))]
    samples=[{'id':p.stem,'points':str(p),'sha256':sha256(p),'columns':[0,1,2],'localize':False} for p in chosen]
    write_json(out/'development20.json',{'role':'development','origin':'user-repurposed competition point directory',
        'selection':'20 random files; seed 20260921; frozen before reconstruction; not historical batch01',
        'seed':20260921,'independent_test':False,'samples':samples})
    historical=[]
    for bid in ['10','1000','2000']:
        p=Path(args.points).resolve()/(bid+'.xyz')
        historical.append({'id':bid,'points':str(p),'sha256':sha256(p),'columns':[0,1,2],'localize':False,
                           'historical_mesh':str(ROOT/'releases/v0.1.0-baseline/models'/(bid+'_lod2.obj'))})
    write_json(out/'historical3.json',{'role':'historical_regression','samples':historical})
    write_json(out/'provenance.json',{'repository_commit':'46a2c3e35cc5d0e715b487020f99574225510e5d',
        'baseline_git_blob_sha256':sha256(out/'baseline_original.py'),'available_points':len(paths),
        'original_batch20_status':'missing_original_training_inputs; not silently substituted'})


if __name__=='__main__':main()
