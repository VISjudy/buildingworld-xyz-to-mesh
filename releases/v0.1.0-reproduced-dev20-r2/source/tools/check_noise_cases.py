from pathlib import Path
import sys,json,traceback
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path[:0]=[str(ROOT),str(HERE)]
import pointcloud_to_mesh as engine
from validate_detail import validate
OUT=ROOT/'work/experiments/noise_review';results=[]
for ident,split in [('1321','xyz'),('144','xyz'),('1048','xyz'),('10','LiDAR_xyz'),('1000','LiDAR_xyz'),('2000','LiDAR_xyz')]:
    try:
        m=engine.reconstruct(ROOT/'data/inputs'/split/f'{ident}.xyz',OUT/f'{ident}.obj')
        report,_=validate(m,m);(OUT/f'{ident}_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        row={'id':ident,'planes':len(m['surface_evidence']),'noise':m['noise_diagnostics'],'topology':m['topology'],'gates':report['gates'],'all_points':report['all_points']}
    except Exception as e:row={'id':ident,'error':repr(e),'traceback':traceback.format_exc()}
    results.append(row);print(json.dumps(row),flush=True)
(OUT/'comparison.json').write_text(json.dumps(results,indent=2),encoding='utf8')
