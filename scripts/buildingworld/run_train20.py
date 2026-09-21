"""Fixed-manifest review batch; retains failures and never resamples."""
from pathlib import Path
import sys,json,time,traceback,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
import pointcloud_to_mesh as engine
from validate_detail import validate
OUT=ROOT/'work/experiments/train20_review';OUT.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'releases/v0.4.1-batch01/reports/selection_manifest.json').read_text(encoding='utf8'))
(OUT/'selection_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
engine_hash=hashlib.sha256((ROOT/'pointcloud_to_mesh.py').read_bytes()).hexdigest()
results=[]
for index,item in enumerate(manifest['samples'],1):
    ident=Path(item['name']).stem;dest=OUT/f'{index:02d}_train_{ident}';dest.mkdir(exist_ok=True)
    row={'review_id':index,'source_id':ident,'source':str(ROOT/'data/inputs/xyz'/item['name']),'points':int(item['points']),'directory':dest.name}
    start=time.time()
    try:
        model=engine.reconstruct(row['source'],dest/f'{ident}.obj')
        row.update(status='mesh_exported',topology=model['topology'],warnings=model['warnings'],roof_patch_count=len(model['surface_evidence']))
        try:
            report,res=validate(model,model)
            report['gates']['all_footprint_components_retained']=model['discarded_footprint_area']<=.01
            report['accepted']=all(report['gates'].values())
            (dest/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
            row.update(accepted=report['accepted'],gates=report['gates'],point_p95=report['all_points']['p95'],point_mean=report['all_points']['mean'],point_coverage_0_15=report['all_points']['coverage_at_0_15'],outline_iou=report['outline']['iou'])
        except Exception as ex:
            row.update(accepted=False,validation_error=repr(ex));(dest/'validation_error.txt').write_text(traceback.format_exc(),encoding='utf8')
    except Exception as ex:
        row.update(status='reconstruction_failed',accepted=False,error=repr(ex));(dest/'failure.txt').write_text(traceback.format_exc(),encoding='utf8')
    row['seconds']=time.time()-start;results.append(row)
    (OUT/'batch_results.json').write_text(json.dumps({'engine_version':engine.VERSION,'engine_sha256':engine_hash,'samples':results},indent=2),encoding='utf8')
    print('RESULT',json.dumps(row,ensure_ascii=False),flush=True)
print('DONE',len(results),'exported',sum(r['status']=='mesh_exported' for r in results),'accepted',sum(r['accepted'] for r in results),flush=True)
