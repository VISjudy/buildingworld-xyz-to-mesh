"""Frozen initial v0.1.0 inference and organizer-format export; no GT or fallback.

Creates a new run directory. Resume reads immutable per-case records and verifies
input/output hashes. ZIP contains only same-name OBJ files at its root.
"""
from pathlib import Path
import argparse,concurrent.futures,contextlib,hashlib,importlib.util,json,os,shutil,subprocess,sys,time,traceback,zipfile
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
sys.dont_write_bytecode=True
import numpy as np
from harness.io import read_points,read_obj,sha256,write_json
from harness.preprocess import canonical_transform,normalize,restore
from official_save_mesh import save_mesh
EXPECTED='8b69b7e4f842d9628085adacdc7b27f73c5772f77b1f3c7f10f053c20458053a'
ALG=None


def initialize(source,run):
    global ALG
    os.environ['MPLCONFIGDIR']=str(Path(run)/'runtime'/f'matplotlib-{os.getpid()}')
    assert sha256(source)==EXPECTED
    spec=importlib.util.spec_from_file_location('initial_v010',source)
    ALG=importlib.util.module_from_spec(spec);spec.loader.exec_module(ALG)


def case(task):
    item,run=task;run=Path(run);bid=item['id'];folder=run/'intermediate'/bid
    folder.mkdir(parents=True,exist_ok=False);output=run/'obj'/f'{bid}.obj'
    assert not output.exists()
    started=time.monotonic();row={'id':bid,'input_sha256':item['sha256'],'status':'failed'}
    try:
        assert sha256(item['path'])==item['sha256'],'Input changed'
        p=read_points(item['path']);origin,scale=canonical_transform(p,30.)
        q=normalize(p,origin,scale)
        row.update(points=len(p),origin=origin.tolist(),scale=float(scale),source_min=p.min(0).tolist(),source_max=p.max(0).tolist())
        staged=folder/'LiDAR_xyz';staged.mkdir()
        np.savetxt(staged/f'{bid}.xyz',q,fmt='%.17g')
        ALG.ROOT=folder;ALG.OUT=folder/'baseline';ALG.OUT.mkdir()
        with(folder/'execution.txt').open('x',encoding='utf-8')as log,contextlib.redirect_stdout(log):ALG.run(bid)
        obj=read_obj(ALG.OUT/f'{bid}_lod2.obj')
        vertices=restore(obj['vertices'],origin,scale)
        # This baseline emits convex planar polygons. Fan triangulation preserves
        # their original winding and adds no vertices or changes to the surface.
        faces=np.asarray([[f[0],f[j],f[j+1]]for f in obj['faces']for j in range(1,len(f)-1)],dtype=np.int64)
        assert len(faces)>0 and np.isfinite(vertices).all()
        save_mesh(str(output),vertices,faces)
        loaded=read_obj(output)
        assert loaded['faces']==faces.tolist(),'Export changed face order/indices'
        err=float(np.abs(loaded['vertices']-vertices).max());assert err<=5.1e-8,'Export coordinate mismatch'
        import trimesh
        mesh=trimesh.Trimesh(vertices=loaded['vertices'],faces=faces,process=False)
        tri=loaded['vertices'][faces];areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)*.5
        degenerate=int((areas<=1e-12).sum())
        row.update(status='generated',vertices=len(vertices),polygon_faces=len(obj['faces']),triangles=len(faces),
                   canonical_obj_sha256=sha256(ALG.OUT/f'{bid}_lod2.obj'),roundtrip_max_error=err,
                   watertight=bool(mesh.is_watertight),winding_consistent=bool(mesh.is_winding_consistent),
                   degenerate_triangles=degenerate,topology_pass=bool(mesh.is_watertight and mesh.is_winding_consistent and degenerate==0),
                   self_intersection='not_checked',output_bounds=[loaded['vertices'].min(0).tolist(),loaded['vertices'].max(0).tolist()])
    except Exception as exc:
        row['error']=f'{type(exc).__name__}: {exc}'
        (folder/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        # Preserve any failed export instead of overwriting it; official empty
        # placeholder is separately attributable to this failed baseline sample.
        if output.exists():shutil.move(str(output),str(folder/'failed_export.obj'))
        save_mesh(str(output),None,None)
    row.update(seconds=round(time.monotonic()-started,4),obj_bytes=output.stat().st_size,obj_sha256=sha256(output))
    write_json(run/'audit/cases'/f'{bid}.json',row)
    return row


def package(run,items):
    rows=[json.loads((run/'audit/cases'/f"{i['id']}.json").read_text(encoding='utf-8'))for i in items]
    expected={f"{i['id']}.obj"for i in items};actual={p.name for p in(run/'obj').iterdir()}
    assert expected==actual and len(expected)==4000
    for item,row in zip(items,rows):
        assert sha256(item['path'])==item['sha256']==row['input_sha256']
        assert sha256(run/'obj'/f"{row['id']}.obj")==row['obj_sha256']
        assert (row['status']=='generated')==(row['obj_bytes']>0)
    name='initial_v0.1.0_test4000_submission.zip';zip_path=run/name
    with zipfile.ZipFile(zip_path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        for i in items:z.write(run/'obj'/f"{i['id']}.obj",arcname=f"{i['id']}.obj")
    with zipfile.ZipFile(zip_path)as z:
        assert len(z.infolist())==4000 and set(z.namelist())==expected
        assert z.testzip() is None
        for row in rows:assert hashlib.sha256(z.read(f"{row['id']}.obj")).hexdigest()==row['obj_sha256']
    generated=[r for r in rows if r['status']=='generated'];failed=[r for r in rows if r['status']!='generated']
    summary={'input_count':4000,'obj_count':4000,'generated_meshes':len(generated),'empty_failure_placeholders':len(failed),
             'topology_pass':sum(r['topology_pass']for r in generated),'failed_ids':[r['id']for r in failed],
             'topology_failed_ids':[r['id']for r in generated if not r['topology_pass']],
             'zip':str(zip_path),'zip_bytes':zip_path.stat().st_size,'zip_sha256':sha256(zip_path),
             'zip_root_only':True,'zip_crc_and_all_entry_hashes_verified':True,'all_input_hashes_rechecked':True,
             'algorithm_sha256':EXPECTED,'coordinate_protocol':'initial report: input-only bbox diagonal 30, restore source coordinates',
             'geometry_changes':'convex polygon fan triangulation for recommended exporter; no fitting/repair/fallback changes',
             'empty_rule':'organizer-recommended save_mesh(None,None), not a successfully reconstructed mesh',
             'platform_uploaded':False,'platform_score':None,'complete432_test130_used':False}
    write_json(run/'audit/summary.json',summary);write_json(run/'audit/results.json',rows)
    print(json.dumps(summary,ensure_ascii=False),flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True)
    ap.add_argument('--workers',type=int,default=6);ap.add_argument('--limit',type=int);ap.add_argument('--resume',action='store_true')
    a=ap.parse_args();src=Path(a.input).resolve();run=Path(a.output).resolve()
    if not a.resume:
        files=sorted(src.glob('*.xyz'),key=lambda p:int(p.stem));assert len(files)==4000
        assert {p.stem for p in files}=={str(i)for i in range(1,4001)}
        run.mkdir(parents=True,exist_ok=False)
        for d in ['obj','audit/cases','source','intermediate','runtime']:(run/d).mkdir(parents=True)
        items=[{'id':p.stem,'path':str(p),'bytes':p.stat().st_size,'sha256':sha256(p)}for p in files]
        write_json(run/'audit/inputs.json',items)
        bundled=Path(__file__).resolve().parent
        frozen=bundled/'algorithm.py' if (bundled/'algorithm.py').exists() else ROOT/'releases/v0.1.0-starter78-standard-v001/source/algorithm.py'
        assert sha256(frozen)==EXPECTED
        shutil.copyfile(frozen,run/'source/algorithm.py')
        for p in [Path(__file__),Path(__file__).with_name('official_save_mesh.py')]:shutil.copyfile(p,run/'source'/p.name)
        helper=bundled/'harness' if (bundled/'harness').exists() else ROOT/'harness'
        shutil.copytree(helper,run/'source/harness',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (run/'source/requirements-lock.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True),encoding='utf-8')
        write_json(run/'audit/protocol.json',{'date':'2026-09-22','workers':a.workers,'algorithm_sha256':EXPECTED,'no_GT':True,
              'source_url':'https://huggingface.co/spaces/BuildingWorld/10thLiDARConference','zip_layout':'1.obj ... 4000.obj, no folders',
              'failure_policy':'official empty OBJ, failures retained','normalization':'input bbox diagonal 30; inverse transform on OBJ',
              'user_authorization':'2026-09-22 explicit inference on challenge 4000; independent of locked paired-data stage'})
    items=json.loads((run/'audit/inputs.json').read_text(encoding='utf-8'));remaining=[];done=[]
    for i in items:
        record=run/'audit/cases'/f"{i['id']}.json"
        if record.exists():
            r=json.loads(record.read_text(encoding='utf-8'));assert sha256(run/'obj'/f"{i['id']}.obj")==r['obj_sha256'];done.append(r)
        else:remaining.append(i)
    if a.limit:remaining=remaining[:a.limit]
    started=time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers,initializer=initialize,initargs=(run/'source/algorithm.py',str(run)))as pool:
        futures={pool.submit(case,(i,str(run))):i for i in remaining}
        with(run/'audit/events.jsonl').open('a',encoding='utf-8')as log:
            for f in concurrent.futures.as_completed(futures):
                row=f.result();done.append(row);log.write(json.dumps(row,ensure_ascii=False)+'\n');log.flush()
                if len(done)%25==0 or len(done)<=8:
                    print(json.dumps({'done':len(done),'generated':sum(r['status']=='generated'for r in done),
                       'failed':sum(r['status']!='generated'for r in done),'last_id':row['id'],'elapsed_seconds':round(time.monotonic()-started,1)}),flush=True)
    if len(done)==4000:package(run,items)
    else:print(f'Smoke complete: {len(done)}/4000; resume the same directory.',flush=True)


if __name__=='__main__':main()
