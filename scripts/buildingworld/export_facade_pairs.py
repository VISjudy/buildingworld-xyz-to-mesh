"""Export audited author pairs; never invent geometry or add artificial point returns."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from harness.io import read_json,read_points,read_obj,write_obj,write_json,sha256
from harness.evaluate import structure_edges


def export(audit_files,output,max_per_split=20):
    out=Path(output);out.mkdir(parents=True,exist_ok=False);records=[]
    for audit_file in audit_files:
        audit=read_json(audit_file);groups={}
        for row in audit['results']:
            if row.get('selected_for_facade_development'):groups.setdefault(row['split'],[]).append(row)
        for split,rows in groups.items():
            for row in rows[:max_per_split] if max_per_split else rows:
                name=audit['kind'];d=out/name/split/row['id'];d.mkdir(parents=True)
                pc=np.load(row['points'],allow_pickle=False) if Path(row['points']).suffix=='.npy' else read_points(row['points'])
                mesh=read_obj(row['mesh']);v=mesh['vertices'];transform=row.get('author_transform')
                if name=='point2building':
                    if not transform or not np.isfinite(transform['scale']) or transform['scale']<=0:raise ValueError('Missing valid author transform')
                    scale=float(transform['scale']);center=np.array(transform['center'],dtype=float)
                    pc=pc*scale+center;v=v*scale+center
                    frame='author_world_coordinates; CRS and vertical datum not independently established'
                else:
                    scale=1.;center=np.zeros(3);frame='author_normalized_coordinates; source CRS transform not supplied in mini'
                np.savetxt(d/'points.xyz',pc,fmt='%.12f')
                write_obj(d/'gt.obj',v,mesh['faces'],mesh['groups'])
                reloaded=read_obj(d/'gt.obj')['vertices'];max_error=float(np.abs(reloaded-v).max())
                if not np.allclose(reloaded,v,rtol=0,atol=1e-5):raise ValueError('OBJ coordinate roundtrip mismatch')
                if not np.allclose(np.loadtxt(d/'points.xyz'),pc,rtol=0,atol=1e-8):raise ValueError('XYZ roundtrip mismatch')
                edges,_=structure_edges(mesh)
                with (d/'wireframe.obj').open('x',encoding='utf-8') as f:
                    for q in v:f.write('v '+' '.join(f'{x:.12f}' for x in q)+'\n')
                    for a,b in edges:f.write(f'l {a+1} {b+1}\n')
                meta={**row,'source_type':audit['source_type'],'coordinate_frame':frame,'export_scale':scale,
                    'export_center':center.tolist(),'max_obj_roundtrip_error':max_error,'inferred_surfaces_added':False,
                    'synthetic_points_added':False,'gt_status':'author_supplied_reference','wireframe_status':'derived_from_GT_mesh_not_independent_annotation',
                    'audit_sha256':sha256(audit_file),'exported_points_sha256':sha256(d/'points.xyz'),'exported_mesh_sha256':sha256(d/'gt.obj')}
                write_json(d/'provenance.json',meta)
                records.append({'dataset':name,'source_type':audit['source_type'],'author_split':split,'id':row['id'],
                    'points':str((d/'points.xyz').resolve()),'gt_mesh':str((d/'gt.obj').resolve()),'provenance':str((d/'provenance.json').resolve()),
                    'facade_points':row['facade_points'],'facade_fraction':row['facade_point_fraction'],'coordinate_frame':frame,
                    'point_sha256':sha256(d/'points.xyz'),'mesh_sha256':sha256(d/'gt.obj')})
    write_json(out/'manifest.json',{'role':'quality_screened_starter_pairs','selection':'bounded prefix of deterministically ordered qualifying audit rows per author split',
        'not_unbiased_benchmark':True,'samples':records,'notes':['Original author split retained','Quality selection cannot replace full author test-set evaluation','No facade, roof or base geometry invented','Only selected pairs exported; complete raw datasets retained separately']})
    (out/'README.md').write_text('''# 带立面配对样例

本目录从已下载作者数据中选择通过当前几何/立面筛选的入门样例，每个数据源、原作者 split 最多 20 对。
`points.xyz`：点云；`gt.obj`：作者提供的参考 Mesh；`wireframe.obj`：从参考 Mesh 派生的结构边；`provenance.json`：来源、坐标变换、审核和哈希。

Point2Building 为真实 ALS，按作者 scale/center 还原源坐标；PolyGNN 为仿真 ALS，保留归一化坐标，不能将其距离直接当米。
未生成任何立面点，也未补造 Mesh 的墙面/底面。作者 trainset/testset 保留，但此质量筛选样例集不代表无偏的完整测试集。
完整下载包和全部配对文件在 `dataset/external/`。这里是数据审计结果，不是重建或训练成绩。
''',encoding='utf-8')
    print('exported',len(records),'pairs',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit-files',nargs='+',required=True);p.add_argument('--output',required=True);p.add_argument('--max-per-split',type=int,default=20)
    export(**vars(p.parse_args()))
