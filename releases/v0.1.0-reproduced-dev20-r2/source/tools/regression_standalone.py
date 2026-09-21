from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT),str(HERE)]
import pointcloud_to_mesh as engine
from validate_detail import validate
out=ROOT/'work/experiments/train20_review/regression_previous3';out.mkdir(exist_ok=True)
results={}
for ident in ['10','1000','2000']:
    m=engine.reconstruct(ROOT/'data/inputs/LiDAR_xyz'/f'{ident}.xyz',out/f'{ident}.obj')
    report,_=validate(m,m)
    (out/f'{ident}_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    results[ident]={'all_points':report['all_points'],'gates':report['gates'],'topology':report['topology']}
(out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print(json.dumps(results,indent=2),flush=True)
