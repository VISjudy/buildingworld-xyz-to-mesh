from pathlib import Path
import sys,json,hashlib,zipfile,collections
from html.parser import HTMLParser
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE.parents[1]/'work/runtime/deps'))
import numpy as np
OUT=ROOT/'work/experiments/train20_batch2';batch=json.loads((OUT/'batch_results.json').read_text(encoding='utf8'))
assert len(batch['samples'])==20
assert hashlib.sha256((ROOT/'pointcloud_to_mesh.py').read_bytes()).hexdigest()==batch['engine_sha256']
previous=json.loads((ROOT/'work/experiments/train20_review/selection_manifest.json').read_text(encoding='utf8'));manifest=json.loads((OUT/'selection_manifest.json').read_text(encoding='utf8'))
assert not ({s['sha256'] for s in previous['samples']}&{s['sha256'] for s in manifest['samples']})
checks=[]
for r in batch['samples']:
    assert r['status']=='mesh_exported'
    dest=OUT/r['directory'];model=json.loads((dest/(r['source_id']+'.json')).read_text(encoding='utf8'));vs=[];fs=[]
    for line in (dest/(r['source_id']+'.obj')).read_text(encoding='utf8').splitlines():
        if line.startswith('v '):vs.append([float(x) for x in line.split()[1:]])
        elif line.startswith('f '):fs.append([int(x)-1 for x in line.split()[1:]])
    assert np.isfinite(vs).all() and np.allclose(vs,model['vertices'],atol=1e-9,rtol=0)
    assert fs==model['faces'] and all(0<=i<len(vs) for f in fs for i in f)
    assert model['algorithm_version']==batch['engine_version']
    assert hashlib.sha256(Path(r['source']).read_bytes()).hexdigest()==model['input_sha256']
    assert (dest/'review.png').is_file()
    checks.append({'review_id':r['review_id'],'source_id':r['source_id'],'round_trip_matches':True})
class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('href','src') and not v.startswith('#'):assert (OUT/v).is_file(),v
Links().feed((OUT/'index.html').read_text(encoding='utf8'))
passed=[r['review_id'] for r in batch['samples'] if r['accepted']]
summary={'tested':20,'obj_exported':20,'all_proxy_gates_passed':len(passed),'passed_review_ids':passed,'topology_passed':sum(r['gates']['topology'] for r in batch['samples']),'total_input_points':sum(r['points'] for r in batch['samples']),'total_excluded_points':sum(r['noise']['excluded_points'] for r in batch['samples']),'engine_version':batch['engine_version'],'engine_sha256':batch['engine_sha256'],'official_score':None,'round_trip_checks':checks,'web_test':{'upload_reconstruction_preview':'verified through browser using xyz/1667.xyz','browser_download':'not verified; automatic approval review timed out and denied the browser action'}}
(OUT/'delivery_verification.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
old=json.loads((ROOT/'work/experiments/train20_review/batch_results.json').read_text(encoding='utf8'))['samples'];new=json.loads((ROOT/'work/experiments/noise_review/comparison.json').read_text(encoding='utf8'))
comparison=[]
for ident in ['1321','144','1048']:
    before=next(r for r in old if r['source_id']==ident);after=next(r for r in new if r['id']==ident)
    comparison.append({'id':ident,'excluded':after['noise']['excluded_points'],'points':after['noise']['input_points'],'before_p95':before['point_p95'],'after_p95':after['all_points']['p95'],'before_faces':before['topology']['faces'],'after_faces':after['topology']['faces']})
(ROOT/'work/experiments/noise_review/before_after_summary.json').write_text(json.dumps(comparison,indent=2),encoding='utf8')
text=['# 第二批 20 栋训练点云：21–40','',f"版本 {batch['engine_version']}；20 个新样例全部导出 OBJ，{len(passed)} 栋通过当前全部观测代理门槛（{', '.join(map(str,passed))}）。其他候选仍需修复，不能视作合格闭合建筑。",'',
'网页：`http://127.0.0.1:8765`。上传 XYZ / TXT，生成 OBJ，可切换点云、网格和叠加，查看排除点与检查报告。停止后运行 `webapp/start.ps1` 启动。', '',
'本目录 `index.html` 是静态六视图检查册；`buildingworld_train20.blend` 为 Blender 总览，场景菜单 `Inspect_21...Inspect_40` 可逐栋检查。陈列进行了等比缩放与平移，OBJ 始终保留源坐标。验证使用全部原始点。', '',
'## 你圈出的两栋是否为噪声','',
'存在噪声的可能，但保守孤立点规则只排除了 1321 的 1/4032 点、144 的 3/4267 点；这不足以证明层叠屋面由孤立噪声造成，也不能排除面内噪声或系统性偏差。两栋的屋面分区与接缝仍有缺陷，新版 P95 甚至变差，因此不能宣称该问题已修复。不要用强滤波抹掉真实凹角、屋脊和小构件。', '',
'| 文件 | 排除点数 | 原 P95 | 新 P95 | 原 / 新面数 |','|---|---:|---:|---:|---:|']
for r in comparison:text.append(f"| {r['id']} | {r['excluded']}/{r['points']} | {r['before_p95']:.4f} | {r['after_p95']:.4f} | {r['before_faces']} / {r['after_faces']} |")
text+=['','P95 是全部原始点到网格的距离，单位为输入坐标单位。没有真值，未计算 CD、ECD 或 FINAL SCORE。', '',
'## 本批结果','', '| 编号 | 训练 ID | 点数 | 排除点 | P95 | 未通过项 |','|---|---|---:|---:|---:|---|']
for r in batch['samples']:text.append(f"| {r['review_id']} | {r['source_id']} | {r['points']} | {r['noise']['excluded_points']} | {r['point_p95']:.4f} | {', '.join(k for k,v in r['gates'].items() if not v) or '无（仅代理验收）'} |")
text+=['','36 / 1983 的屋面邻接存在歧义。该样例保留已拟合面，跳过无法可靠确定的连接墙，记录 unresolved_partition_edges，并强制邻接验收失败；这是可检查的候选输出，不是自动修复成功。', '',
'网页上传、生成、结果预览已通过浏览器实际操作；浏览器下载按钮测试被自动审批超时拦截，未标记验证成功。20 个本地 OBJ 已重新解析并核对坐标与面索引。']
(OUT/'README.md').write_text('\n'.join(text)+'\n',encoding='utf8')
with zipfile.ZipFile(OUT/'train20_batch2_objs.zip','w',zipfile.ZIP_DEFLATED) as z:
    for path in [ROOT/'pointcloud_to_mesh.py',ROOT/'BUILDING_RECONSTRUCTION_ALGORITHM.md',ROOT/'requirements-reconstruction.txt',OUT/'README.md',OUT/'selection_manifest.json',OUT/'batch_results.json',OUT/'delivery_verification.json',OUT/'feedback.csv']:z.write(path,path.name)
    for r in batch['samples']:
        for name in [r['source_id']+'.obj',r['source_id']+'.json','validation.json']:
            path=OUT/r['directory']/name;z.write(path,str(path.relative_to(OUT)))
print(json.dumps({k:v for k,v in summary.items() if k!='round_trip_checks'},indent=2))
