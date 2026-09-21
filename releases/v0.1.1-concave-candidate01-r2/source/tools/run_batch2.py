"""New fixed training samples; excludes the previous batch and exact duplicates."""
from pathlib import Path
import csv,sys,json,hashlib,subprocess,time,shutil,traceback,os
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path[:0]=[str(ROOT),str(HERE.parents[1]/'work/runtime/deps')]
import numpy as np
import pointcloud_to_mesh as engine
OUT=ROOT/'work/experiments/train20_batch2';OUT.mkdir(parents=True,exist_ok=True)
manifest_path=OUT/'selection_manifest.json'
if not manifest_path.exists():
    manifest_path.write_bytes((ROOT/'releases/v0.5.1-batch02/reports/selection_manifest.json').read_bytes())
if not manifest_path.exists():
    previous=json.loads((ROOT/'releases/v0.4.1-batch01/reports/selection_manifest.json').read_text(encoding='utf8'))['samples'];excluded={r['sha256'] for r in previous}
    rows=list(csv.DictReader((HERE.parents[1]/'work/audit/pointcloud_inventory.csv').open(encoding='utf-8-sig')));unique={}
    for r in rows:
        if r['split']!='xyz' or r['sha256'] in excluded:continue
        if min(float(r[a+'_max'])-float(r[a+'_min']) for a in 'xyz')<=.2:continue
        unique.setdefault(r['sha256'],r)
    rows=sorted(unique.values(),key=lambda r:(int(r['points']),r['name']));rng=np.random.default_rng(20260921)
    samples=[rows[int(rng.choice(ix))] for ix in np.array_split(np.arange(len(rows)),20)]
    manifest_path.write_text(json.dumps({'seed':20260921,'source':'xyz training','selection':'20 equal-frequency point-count strata; excludes previous 20 source hashes; exact duplicates removed; XYZ spans > 0.2; fixed before reconstruction','samples':samples},indent=2),encoding='utf8')
manifest=json.loads(manifest_path.read_text(encoding='utf8'));rows=[];digest=hashlib.sha256((ROOT/'pointcloud_to_mesh.py').read_bytes()).hexdigest()
for index,item in enumerate(manifest['samples'],21):
    ident=Path(item['name']).stem;dest=OUT/f'{index:02d}_train_{ident}';dest.mkdir(exist_ok=True);start=time.time()
    source=str(ROOT/'data/inputs/xyz'/item['name']);(dest/'request.json').write_text(json.dumps({'source':source,'noise':'conservative'}),encoding='utf8')
    row={'review_id':index,'source_id':ident,'source':source,'points':int(item['points']),'directory':dest.name,'accepted':False}
    try:
        with (dest/'run.log').open('w',encoding='utf8') as log:
            proc=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'webapp/worker.py'),str(dest)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=600)
        result=json.loads((dest/'result.json').read_text(encoding='utf8'))
        if result['status']!='complete':raise RuntimeError(result.get('error','Worker failed'))
        for ext in ['obj','json']:shutil.copy2(dest/f'model.{ext}',dest/f'{ident}.{ext}')
        model=json.loads((dest/'model.json').read_text(encoding='utf8'))
        row.update(status='mesh_exported',topology=model['topology'],noise=model['noise_diagnostics'],warnings=model['warnings'],roof_patch_count=len(model['surface_evidence']))
        if 'validation' in result:
            report=result['validation'];row.update(accepted=report['accepted'],gates=report['gates'],point_p95=report['all_points']['p95'],point_mean=report['all_points']['mean'],point_coverage_0_15=report['all_points']['coverage_at_0_15'],outline_iou=report['outline']['iou'])
        else:row['validation_error']=result.get('validation_error','Validation unavailable')
    except Exception as e:row.update(status='reconstruction_failed',error=repr(e));(dest/'failure.txt').write_text(traceback.format_exc(),encoding='utf8')
    row['seconds']=time.time()-start;rows.append(row)
    payload={'engine_version':engine.VERSION,'engine_sha256':digest,'batch':'second20','samples':rows}
    tmp=OUT/'batch_results.tmp';tmp.write_text(json.dumps(payload,indent=2),encoding='utf8');tmp.replace(OUT/'batch_results.json')
    print('RESULT',index,ident,row['status'],'accepted',row['accepted'],'P95',row.get('point_p95'),flush=True)
print('DONE',len(rows),'exported',sum(r['status']=='mesh_exported' for r in rows),'accepted',sum(r['accepted'] for r in rows),flush=True)
