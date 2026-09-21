from pathlib import Path
import sys,json,hashlib,zipfile,collections
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE.parents[1]/'work/runtime/deps'))
import numpy as np
from html.parser import HTMLParser
OUT=ROOT/'work/experiments/train20_review';data=json.loads((OUT/'batch_results.json').read_text(encoding='utf8'))
assert len(data['samples'])==20
class LocalLinks(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ('href','src') and not value.startswith('#'):
                assert (OUT/value).is_file(),value
LocalLinks().feed((OUT/'index.html').read_text(encoding='utf8'))
assert hashlib.sha256((ROOT/'pointcloud_to_mesh.py').read_bytes()).hexdigest()==data['engine_sha256']
checks=[]
for row in data['samples']:
    if row['status']!='mesh_exported':continue
    dest=OUT/row['directory'];path=dest/(row['source_id']+'.obj');m=json.loads(path.with_suffix('.json').read_text(encoding='utf8'))
    vertices=[];faces=[]
    for line in path.read_text(encoding='utf8').splitlines():
        if line.startswith('v '):vertices.append([float(v) for v in line.split()[1:]])
        elif line.startswith('f '):faces.append([int(v)-1 for v in line.split()[1:]])
    assert faces==m['faces'];assert np.isfinite(vertices).all();assert np.allclose(vertices,m['vertices'],atol=1e-9,rtol=0)
    assert all(0<=i<len(vertices) for f in faces for i in f)
    assert m['algorithm_version']==data['engine_version']
    assert hashlib.sha256(Path(row['source']).read_bytes()).hexdigest()==m['input_sha256']
    checks.append({'review_id':row['review_id'],'obj':str(path),'vertices':len(vertices),'faces':len(faces),'round_trip_matches':True})
counts=collections.Counter(k for r in data['samples'] for k,v in r.get('gates',{}).items() if not v)
summary={'algorithm_version':data['engine_version'],'engine_sha256':data['engine_sha256'],'tested':20,'obj_exported':len(checks),'all_proxy_gates_passed':sum(r.get('accepted',False) for r in data['samples']),'topology_gate_passed':sum(r.get('gates',{}).get('topology',False) for r in data['samples']),'gate_failure_counts':dict(counts),'official_CD_ECD_final_score':None,'obj_round_trip_checks':checks}
(OUT/'delivery_verification.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
regression=json.loads((OUT/'regression_previous3/results.json').read_text(encoding='utf8'))
print('REGRESSION',[(k,r['gates']) for k,r in regression.items()],flush=True)
lines=['# 20 栋训练样例检查包','',f"算法：{data['engine_version']}。固定抽样 20 栋，导出 {len(checks)} 个 OBJ；{summary['all_proxy_gates_passed']} 栋通过当前全部观测代理门槛，{summary['topology_gate_passed']} 栋通过拓扑门槛。其余均保留供人工检查，不能作为合格建筑模型使用。",'',
'打开 `index.html` 逐栋查看六视图与下载链接，或在 Blender 打开 `buildingworld_train20.blend`。总览左为点云、右为网格；场景菜单 `Inspect_01...Inspect_20` 提供单栋叠加，关闭 `02_ALIGNED_XYZ_TOGGLE` 只看网格。`03_FULL_XYZ_VERTICES_TOGGLE` 保存全部输入顶点；总览与叠加显示最多 3500 个真实点以便浏览。', '',
'OBJ 保持源 XYZ 坐标。Blender 单栋采用同一平移/等比缩放显示点云和网格，缩放仅用于陈列，不能跨栋比较显示尺寸。验证使用全部输入点，不使用显示抽样。', '',
'没有真值网格和官方评测脚本，CD、ECD、NC、V_Ratio、F_Ratio、FINAL SCORE 均未计算。P95、覆盖率与轮廓 IoU 是观测一致性代理。规则阈值没有为本批次放宽。', '',
'## 检查结果','', '| 编号 | 训练 ID | 点数 | 点面 P95 | 0.15 内比例 | 未通过门槛 |','|---|---|---:|---:|---:|---|']
for r in data['samples']:
    errors=', '.join(k for k,v in r.get('gates',{}).items() if not v) or r.get('error','通过代理门槛')
    lines.append(f"| {r['review_id']:02d} | {r['source_id']} | {r['points']} | {r.get('point_p95',float('nan')):.4f} | {r.get('point_coverage_0_15',0):.1%} | {errors} |")
lines+=['','## 原 3 栋回归检查','', '旧 V2 产物保留未改。新独立脚本的回归结果如下；拓扑失败需要继续修复，不能用几何误差较小掩盖：','']
for ident,r in regression.items():lines.append(f"- {ident}：全点 P95 {r['all_points']['p95']:.4f}；未通过：{', '.join(k for k,v in r['gates'].items() if not v) or '无'}；开放边 {r['topology']['open_edges']}。")
lines+=['','下一轮优先检查：屋面交汇的共形拓扑、复杂/低坡屋面分区、高低附楼的接缝位置、轮廓规整对斜边与小凹角的影响。', '', '反馈请写“编号 + 部位 + 问题”，例如“14，主屋脊，低坡屋顶被压平”。可填 `feedback.csv`，也可在 `index.html` 填写后导出 JSON。']
(OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
with zipfile.ZipFile(OUT/'train20_objs.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in [ROOT/'pointcloud_to_mesh.py',ROOT/'BUILDING_RECONSTRUCTION_ALGORITHM.md',ROOT/'requirements-reconstruction.txt',OUT/'README.md',OUT/'selection_manifest.json',OUT/'batch_results.json',OUT/'feedback.csv',OUT/'delivery_verification.json']:
        z.write(p,p.name)
    for row in data['samples']:
        dest=OUT/row['directory']
        for name in [row['source_id']+'.obj',row['source_id']+'.json','validation.json']:
            p=dest/name
            if p.exists():z.write(p,str(p.relative_to(OUT)))
print(json.dumps({k:v for k,v in summary.items() if k!='obj_round_trip_checks'},indent=2),flush=True)
