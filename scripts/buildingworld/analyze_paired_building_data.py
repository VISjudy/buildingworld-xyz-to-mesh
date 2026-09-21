"""Safe archive extraction and explicit facade-evidence auditing of author datasets.

Never execute bundled scripts, pickle/torch checkpoints, or infer GT from a prediction.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path,PurePosixPath
import shutil
import sys
import tarfile
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from harness.io import read_obj,read_points,sha256,write_json
from harness.evaluate import prepare,closest,structure_edges,topology


def extract(archive,output,kind):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False)
    records=[];skipped=Counter()
    with tarfile.open(archive,'r|gz') as tar:
        for member in tar:
            rel=PurePosixPath(member.name)
            if rel.is_absolute() or '..' in rel.parts or any(':' in x for x in rel.parts):raise ValueError('Unsafe archive path')
            if member.isdir():continue
            if not member.isfile():raise ValueError('Archive links/devices are not allowed')
            suffix=rel.suffix.lower()
            wanted=(kind=='point2building' and 'datasets' in rel.parts and suffix in ['.obj','.xyz','.json','.txt']) or (
                kind=='polygnn_mini' and ('03_meshes' in rel.parts or '04_pts' in rel.parts or rel.name in ['trainset.txt','testset.txt']))
            if not wanted:skipped[suffix]+=1;continue
            dest=(out/str(rel)).resolve()
            if not dest.is_relative_to(out):raise ValueError('Archive path escapes output')
            if member.size>512*1024**2:raise ValueError('Unexpectedly large individual dataset file')
            dest.parent.mkdir(parents=True,exist_ok=True)
            h=hashlib.sha256()
            with tar.extractfile(member) as src,dest.open('xb') as dst:
                while block:=src.read(1024*1024):dst.write(block);h.update(block)
            records.append({'path':dest.relative_to(out).as_posix(),'bytes':member.size,'sha256':h.hexdigest()})
    write_json(out/'extraction_manifest.json',{'archive_sha256':sha256(archive),'kind':kind,'files':records,'skipped_extensions':dict(skipped),'executed_bundled_code':False})
    print(json.dumps({'files_extracted':len(records),'skipped':dict(skipped)}),flush=True)


def catalog(root,kind):
    root=Path(root);pairs=[];missing=[]
    if kind=='point2building':
        for directory in sorted(root.glob('resources/datasets/*/*')):
            if not directory.is_dir():continue
            meshes={p.stem:p for p in (directory/'meshes').glob('*.obj')}
            points={p.stem:p for p in (directory/'pointclouds').glob('*.xyz')}
            info=json.loads((directory/'info.json').read_text()) if (directory/'info.json').is_file() else {}
            for bid in sorted(points.keys()&meshes.keys()):
                pairs.append({'id':bid,'city':directory.parent.name,'split':directory.name,'points':str(points[bid].resolve()),
                    'mesh':str(meshes[bid].resolve()),'author_transform':info.get(bid)})
            missing.extend([{'city':directory.parent.name,'split':directory.name,'unpaired_point_ids':sorted(points.keys()-meshes.keys()),'unpaired_mesh_ids':sorted(meshes.keys()-points.keys())}])
    else:
        raw=root/'raw';meshes={p.stem:p for p in (raw/'03_meshes').glob('*.obj')};points={p.stem:p for p in (raw/'04_pts').glob('*.npy')}
        splits={}
        for name in ['trainset','testset']:
            for bid in (raw/(name+'.txt')).read_text().splitlines():
                if bid in splits:raise ValueError('Author split overlap: '+bid)
                splits[bid]=name
        for bid in sorted(points.keys()&meshes.keys()):pairs.append({'id':bid,'city':'Munich','split':splits.get(bid,'unspecified'),
            'points':str(points[bid].resolve()),'mesh':str(meshes[bid].resolve()),'author_transform':None})
        missing=[{'unpaired_point_ids':sorted(points.keys()-meshes.keys()),'unpaired_mesh_ids':sorted(meshes.keys()-points.keys())}]
    return pairs,missing


def audit_pair(row):
    p=np.load(row['points'],allow_pickle=False) if Path(row['points']).suffix=='.npy' else read_points(row['points'])
    if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all():raise ValueError('Expected finite Nx3 points')
    obj=read_obj(row['mesh']);mesh,_,origin=prepare(obj)
    diag=float(np.linalg.norm(np.ptp(obj['vertices'],axis=0)));height=float(np.ptp(obj['vertices'][:,2]));zmin=float(obj['vertices'][:,2].min())
    if height<=1e-8 or diag<=1e-8:raise ValueError('Degenerate building extent')
    tolerance=.005*diag
    distances,idx=closest(mesh,p-origin)
    faces=obj['vertices'][mesh.faces]
    low=faces[:,:,2].min(axis=1);high=faces[:,:,2].max(axis=1)
    normals=mesh.face_normals
    walls=(np.abs(normals[:,2])<=np.sin(np.deg2rad(10)))&(low<=zmin+.1*height)&((high-low)>=.25*height)
    bottom=(np.abs(normals[:,2])>=.9)&(high<=zmin+.05*height)
    # Exclude roofline/base coincidences: evidence must lie well inside the wall's vertical interval.
    mask=walls[idx]&(distances<=tolerance)&(p[:,2]>low[idx]+.1*(high[idx]-low[idx]))&(p[:,2]<high[idx]-.1*(high[idx]-low[idx]))
    count=int(mask.sum());fraction=float(mask.mean());span=float(np.ptp(p[mask,2])/height) if count>1 else 0.
    edges,incidence=structure_edges(obj);top=topology(obj,mesh,incidence)
    closed=top['watertight'] and not top['inconsistent_winding_edges'] and not top['degenerate_triangles']
    evidence=count>=10 and fraction>=.005 and span>=.15
    full_surfaces=bool(walls.any() and bottom.any() and closed)
    return {**row,'points_sha256':sha256(row['points']),'mesh_sha256':sha256(row['mesh']),'point_count':len(p),'mesh_vertices':len(obj['vertices']),
        'mesh_polygon_faces':len(obj['faces']),'height_in_author_units':height,'bbox_diagonal_in_author_units':diag,
        'wall_triangles':int(walls.sum()),'base_triangles':int(bottom.sum()),'watertight':top['watertight'],
        'winding_errors':len(top['inconsistent_winding_edges']),'signed_volume':top['signed_volume'],
        'point_to_reference_p95':float(np.quantile(distances,.95)),'p95_fraction_diagonal':float(np.quantile(distances,.95)/diag),
        'facade_points':count,'facade_point_fraction':fraction,'facade_vertical_span_fraction':span,
        'facade_observation_pass':evidence,'closed_wall_base_mesh_pass':full_surfaces,
        'selected_for_facade_development':evidence and full_surfaces and float(np.quantile(distances,.95)/diag)<=.05,
        'self_intersection':'not_checked','semantic_accuracy':'reference_model_not_perfect_physical_truth'}


def screen_topology(root,output,kind):
    pairs,_=catalog(root,kind);rows=[]
    for i,row in enumerate(pairs):
        try:
            obj=read_obj(row['mesh']);m,_,_=prepare(obj)
            ok=bool(m.is_watertight and m.is_winding_consistent and (m.area_faces>1e-12).all())
            rows.append({'id':row['id'],'city':row['city'],'split':row['split'],'closed_consistent':ok})
        except Exception as exc:rows.append({'id':row['id'],'city':row['city'],'split':row['split'],'closed_consistent':False,'error':str(exc)})
        if (i+1)%2000==0:print('topology',i+1,'/',len(pairs),flush=True)
    write_json(output,{'kind':kind,'scope':'all author meshes; strict triangle adjacency, no repair','results':rows,
                       'closed_count':sum(r['closed_consistent'] for r in rows)})
    print('closed',sum(r['closed_consistent'] for r in rows),'/ total',len(rows),flush=True)


def audit(root,output,kind,per_split,topology_screen=None):
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    pairs,missing=catalog(root,kind)
    write_json(out/'catalog.json',{'kind':kind,'pairs':pairs,'unpaired':missing})
    # Deterministic hash order avoids selecting the first spatially neighboring files only.
    grouped={}
    allowed=None
    if topology_screen:
        with Path(topology_screen).open(encoding='utf-8') as f:screen=json.load(f)
        allowed={(r['city'],r['split'],r['id']) for r in screen['results'] if r['closed_consistent']}
    for row in pairs:
        if allowed is None or (row['city'],row['split'],row['id']) in allowed:
            grouped.setdefault((row['city'],row['split']),[]).append(row)
    chosen=[]
    for group in sorted(grouped):
        ordered=sorted(grouped[group],key=lambda r:hashlib.sha256(('facade-audit-v1:'+r['id']).encode()).hexdigest())
        chosen.extend(ordered[:per_split] if per_split else ordered)
    results=[]
    for i,row in enumerate(chosen):
        try:result={**audit_pair(row),'status':'audited'}
        except Exception as e:result={**row,'status':'failed','error':str(e)}
        results.append(result)
        if (i+1)%10==0:print(kind,i+1,'/',len(chosen),flush=True)
    summary={'kind':kind,'source_type':'real_airborne_lidar' if kind=='point2building' else 'simulated_airborne_lidar',
        'catalog_pair_count':len(pairs),'eligible_pool_by_city_split':{':'.join(k):len(v) for k,v in grouped.items()},
        'topology_prescreen':str(topology_screen) if topology_screen else None,
        'audited_count':len(results),'audit_sampling':'SHA256(facade-audit-v1:id) order, bounded per author city/split; if prescreen supplied, only closed meshes. Not representative of the full distribution.',
        'thresholds':{'wall_angle_from_vertical_degrees':10,'point_distance_fraction_diagonal':.005,'min_points':10,'min_point_fraction':.005,'min_vertical_span_fraction':.15,'max_p95_fraction_diagonal':.05},
        'results':results,'selected_count':sum(r.get('selected_for_facade_development',False) for r in results),
        'limitations':['Airborne facade coverage remains incomplete','Nearest GT wall plus vertical interior test is a conservative geometric proxy, not manual semantic labels','Units may be author normalized; do not label distances metres without transform verification','Self intersection not checked','This audit is data QA, not reconstruction algorithm accuracy']}
    write_json(out/'audit.json',summary)
    write_json(out/'facade_development_candidates.json',{'role':'data_audit_development_not_sealed_test','kind':kind,
        'source_type':summary['source_type'],'samples':[r for r in results if r.get('selected_for_facade_development')]})
    print(json.dumps({k:v for k,v in summary.items() if k not in ['results','limitations']}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('extract');q.add_argument('--archive',required=True);q.add_argument('--output',required=True);q.add_argument('--kind',choices=['point2building','polygnn_mini'],required=True)
    q=s.add_parser('audit');q.add_argument('--root',required=True);q.add_argument('--output',required=True);q.add_argument('--kind',choices=['point2building','polygnn_mini'],required=True);q.add_argument('--per-split',type=int,default=60);q.add_argument('--topology-screen')
    q=s.add_parser('screen-topology');q.add_argument('--root',required=True);q.add_argument('--output',required=True);q.add_argument('--kind',choices=['point2building','polygnn_mini'],required=True)
    args=vars(p.parse_args());command=args.pop('command');{'extract':extract,'audit':audit,'screen-topology':screen_topology}[command](**args)
