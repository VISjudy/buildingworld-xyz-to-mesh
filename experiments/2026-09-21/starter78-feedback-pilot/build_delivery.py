"""Publish this preregistered pilot into new immutable release/report directories.

Run from the repository root after both transfer batches and Blender renders finish.
No reconstruction, parameter search or sealed-data access occurs here.
"""
from pathlib import Path
import csv
import html
import json
import shutil
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from harness.io import read_json, write_json, sha256, read_obj
from harness.preprocess import restore
from harness.pilot_analysis import summarize, paired

WORK = ROOT / 'work/experiments/2026-09-21/starter78-feedback-pilot'
OUT = ROOT / 'reports/2026-09-21-starter78-feedback-pilot'
ARMS = ['baseline', 'F0', 'F3', 'transfer_original', 'transfer_evolved']
VERSIONS = dict(zip(ARMS, ['v0.1.0-starter78-standard-v001', 'v0.1.2-pilot-f0-v001',
    'v0.1.2-pilot-f3-v001', 'v0.1.2-transfer-original-v001', 'v0.1.2-transfer-evolved-v001']))
TITLES = {'baseline':'v0.1.0 + 统一预处理', 'F0':'F0 无结果反馈', 'F3':'F3 结构化反馈',
          'transfer_original':'原始 Harness', 'transfer_evolved':'演化 Harness'}


def copy_file(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise FileExistsError(dst)
    shutil.copyfile(src, dst)


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    assets = OUT / 'assets'; assets.mkdir()
    raw = {a: read_json(WORK / a / 'results.json') for a in ARMS}
    rows = {a: r['samples'] for a, r in raw.items()}
    ids = {a: {r['id']: r for r in rs} for a, rs in rows.items()}
    partitions = {n: {r['id'] for r in read_json(WORK / 'setup' / (n+'.json'))['samples']}
                  for n in ['discovery', 'selection', 'transfer', 'all78']}
    select = lambda arm, part: [r for r in rows[arm] if r['id'] in partitions[part]]
    comparisons = {part: {a: paired(select('baseline', part), select(a, part))
                         for a in (['F0', 'F3'] if part != 'transfer_policy' else [])}
                   for part in ['discovery', 'selection', 'transfer', 'all78']}
    comparisons['transfer_policy'] = {a: paired(select('baseline','transfer'), rows[a]) for a in ARMS[3:]}
    comparisons['transfer_evolved_vs_original'] = paired(rows[ARMS[3]], rows[ARMS[4]])
    summary = {'protocol': read_json(WORK/'setup/preregistration.json'),
        'standardization': read_json(ROOT.parent/'dataset/processed/standardized_pairs_v001/verification.json'),
        'summaries': {a:summarize(r) for a,r in rows.items()}, 'comparisons':comparisons,
        'budget': {'reconstruction_attempts':sum(len(v) for v in rows.values()),
                   'candidate_proposals':4, 'meta_policy_proposals':1, 'seeds_per_arm':1,
                   'base_algorithm_seed':739, 'max_changed_lines_per_candidate':80,
                   'max_tool_calls_per_candidate':6, 'model':'same inherited runtime; exact provider snapshot unavailable',
                   'token_counts':None, 'token_matched':False,
                   'parallel_batch_wall_seconds_not_inference_only':{a:r['wall_seconds'] for a,r in raw.items()}},
        'limitations':['All 78 are development; partitions are ID-disjoint, not city/space independent.',
          'Local CD/ECD/NC; canonical diagonal 30, not metres or official scores.',
          'One proposal and one seed per condition; neither statistical efficacy nor recursive improvement established.',
          'Complete train432/test130 not reconstructed; exact model/token control unavailable.',
          'Topology pass excludes a comprehensive prediction self-intersection test.',
          'F0 and F3 are sibling candidates from the same baseline, not successive algorithm parents.']}
    assert len({r['evaluator_sha256'] for r in raw.values()}) == 1
    assert sha256(WORK/'transfer_proposals/original/initial_algorithm.py') == sha256(WORK/'transfer_proposals/evolved/initial_algorithm.py') == raw['baseline']['source_sha256']
    assert read_json(WORK/'transfer_proposals/original/feedback.json') == read_json(WORK/'transfer_proposals/evolved/feedback.json')
    verification = {'same_evaluator':True, 'same_transfer_initial_algorithm':True,
                    'same_transfer_evidence_content':True, 'roundtrips':[], 'render_hashes':[]}
    for arm in ARMS:
        for sample in read_json(WORK/arm/'inputs.json')['samples']:
            result = ids[arm][sample['id']]
            if result['status'] != 'evaluated': continue
            folder = WORK/arm/'samples'/sample['id']
            model, source = read_obj(folder/'model.obj'), read_obj(folder/'model_source.obj')
            transform = read_json(sample['transform'])
            expected = restore(model['vertices'], transform['origin'], transform['scale'])
            error = float(np.abs(source['vertices'] - expected).max())
            assert model['faces'] == source['faces'] and error <= 1e-5
            assert sha256(folder/'model.obj') == result['mesh_sha256']
            verification['roundtrips'].append({'arm':arm, 'id':sample['id'], 'max_error_source_units':error})
    for folder, mapping in [('renders', {'baseline':'baseline','previous':'F0','current':'F3'}),
                            ('transfer_renders', {'baseline':'baseline','previous':'transfer_original','current':'transfer_evolved'})]:
        for r in read_json(WORK/folder/'render_manifest.json')['samples']:
            for role, arm in mapping.items():
                if ids[arm][r['id']]['status'] == 'evaluated':
                    assert r['source_hashes'][role] == ids[arm][r['id']]['mesh_sha256']
                    verification['render_hashes'].append({'arm':arm,'id':r['id'],'verified':True})
    write_json(OUT/'summary.json',summary); write_json(OUT/'verification.json',verification)
    copy_file(ROOT/'config/data_protocol_v001.json',OUT/'data_protocol_v001.json')
    copy_file(WORK/'setup/preregistration.json',OUT/'preregistration.json')
    for name in ['F0','F3']:
        copy_file(WORK/'proposals'/name/'proposal.json',OUT/f'{name}_proposal.json')
    for name in ['original','evolved']:
        for file in ['proposal.json','policy.json']:
            copy_file(WORK/'transfer_proposals'/name/file,OUT/f'transfer_{name}_{file}')
    copy_file(WORK/'meta/experience.json',OUT/'meta_experience.json')
    copy_file(WORK/'meta/policy_evolved.json',OUT/'policy_evolved.json')
    flat = []
    for arm, rs in rows.items():
        copy_file(WORK/arm/'results.json',OUT/f'{arm}_results.json')
        for row in rs:
            base = ids['baseline'][row['id']]
            rec = {k:row.get(k) for k in ['id','stratum','status','CD','ECD','NC','p95','topology_pass','seconds']}
            rec['arm'] = arm
            rec['partition'] = next(n for n in ['discovery','selection','transfer'] if row['id'] in partitions[n])
            for metric in ['CD','ECD','NC','p95']:
                rec['delta_'+metric] = row[metric]-base[metric] if row['status'] == base['status'] == 'evaluated' else None
            rec['classification'] = ('failed' if row['status'] != 'evaluated' else
                'recovered' if base['status'] != 'evaluated' else
                'unchanged' if abs(rec['delta_CD']) <= 1e-9 and abs(rec['delta_ECD']) <= 1e-9 else
                'improved' if rec['delta_CD'] <= 1e-9 and rec['delta_ECD'] <= 1e-9 else 'regressed_or_mixed')
            flat.append(rec)
    with (OUT/'per_building.csv').open('x',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
    cards=[]; thumbs=[]
    for phase, part, folder, labels in [('first','all78','renders',['Input cloud','v0.1.0 + preprocess','F0 (sibling arm)','F3 (sibling arm)','Reference mesh','F3 + input']),
          ('transfer','transfer','transfer_renders',['Input cloud','Same initial v0.1.0','Original Harness','Evolved Harness','Reference mesh','Evolved + input'])]:
        for bid in sorted(partitions[part]):
            views=[]
            for view in ['oblique','opposite','top','front','back','left','right']:
                canvas=Image.new('RGB',(1920,312),'#f1f4f5'); draw=ImageDraw.Draw(canvas)
                for col,(role,title) in enumerate(zip(['input','baseline','previous','current','reference','overlay'],labels)):
                    draw.text((col*320+8,7),title,font=font,fill='#213541')
                    src=WORK/folder/f'{bid}_{view}_{role}.png'
                    if src.exists():canvas.paste(Image.open(src).convert('RGB'),(col*320,32))
                    else:draw.text((col*320+50,170),'FAILED / no output',font=font,fill='#ae332d')
                name=f'{phase}_{bid}_{view}.jpg';canvas.save(assets/name,quality=86)
                views.append(name)
                if view=='oblique' and phase=='first':thumbs.append((bid,canvas.resize((960,156))))
            arms=['baseline','F0','F3'] if phase=='first' else ['baseline','transfer_original','transfer_evolved']
            lines=[]
            for a in arms:
                r=ids[a][bid]
                lines.append(f"{TITLES[a]}："+ (f"CD {r['CD']:.4f} / ECD {r['ECD']:.4f} / NC {r['NC']:.4f}" if r['status']=='evaluated' else '失败'))
            cards.append(f'<article data-phase="{phase}" data-building="{bid}"><h3>{bid}</h3><p>'+html.escape('；'.join(lines))+f'</p><img loading="lazy" src="assets/{views[0]}" alt="{bid} 同相机输入、基准、两候选、参考和叠加图"><details><summary>另外六个固定视角</summary>'+''.join(f'<img loading="lazy" src="assets/{v}" alt="{bid} {v.rsplit("_",1)[1][:-4]} 视角">' for v in views[1:])+'</details></article>')
    for page in range(0,len(thumbs),13):
        contact=Image.new('RGB',(960,13*184),'white');draw=ImageDraw.Draw(contact)
        for j,(bid,im) in enumerate(thumbs[page:page+13]):
            draw.text((4,j*184),bid,font=font,fill='#213541');contact.paste(im,(0,j*184+25))
        contact.save(assets/f'overview_{page//13+1}.jpg',quality=88)
    # Two source-specific panels; no pooled distance average or invented uncertainty.
    fig,axs=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for ax,source in zip(axs,['real_zurich','synthetic_mini']):
        for j,arm in enumerate(['F0','F3']):
            vals=[r['delta_CD'] for r in flat if r['arm']==arm and r['stratum']==source and r['delta_CD'] is not None]
            ax.scatter(vals,np.full(len(vals),j)+np.linspace(-.15,.15,len(vals)),alpha=.6,s=18,label=arm)
            ax.scatter(np.mean(vals),j,marker='D',s=70,edgecolors='black',zorder=4)
            ax.text(.03,.90-j*.1,f'{arm}: n={len(vals)}, mean={np.mean(vals):+.4f}',transform=ax.transAxes,fontsize=9)
        ax.axvline(0,color='#666',lw=1);ax.set_yticks([0,1],['F0','F3']);ax.set_title(source)
        ax.set_xlabel('Paired CD delta vs baseline (canonical units)');ax.grid(axis='x',alpha=.2)
    fig.savefig(assets/'paired_cd.svg');fig.savefig(assets/'paired_cd.png',dpi=150);plt.close(fig)
    table=''
    for arm in ARMS:
        for source,group in summary['summaries'][arm].items():
            part='all78' if arm in ARMS[:3] else 'transfer_policy'
            delta=comparisons[part][arm]['by_source'][source]['paired_mean_delta'] if arm!='baseline' else None
            table+=f'<tr><td>{TITLES[arm]}</td><td>{source}</td><td>{group["success"]}/{group["attempted"]}</td><td>{group["topology_pass"]}/{group["success"]}</td><td>{delta["CD"]:+.5f}</td><td>{delta["ECD"]:+.5f}</td></tr>' if delta else f'<tr><td>{TITLES[arm]}</td><td>{source}</td><td>{group["success"]}/{group["attempted"]}</td><td>{group["topology_pass"]}/{group["success"]}</td><td>基准</td><td>基准</td></tr>'
    transfer = comparisons['transfer_evolved_vs_original']
    transfer_claim = '本轮没有观察到演化策略优于原始策略；应保留这一负结果。' if transfer['decision']=='not_promoted' else '本轮演化策略达到描述性采用门槛；仍需多轮、多种子验证。'
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>78 对外部反馈与经验迁移小试</title><style>
body{margin:0;background:#f3f5f5;color:#20333f;font:16px/1.75 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1180px;margin:auto;padding:32px 20px}h1{font-size:clamp(27px,4vw,42px);line-height:1.3}h2{margin-top:40px}p{max-width:1000px}a{color:#07616d}img{max-width:100%;height:auto}article,section{background:white;padding:22px;margin:18px 0;border:1px solid #dce3e5;border-radius:8px}article h3{overflow-wrap:anywhere;font-size:16px}article p{font-size:14px}table{border-collapse:collapse;width:100%;white-space:nowrap}td,th{padding:10px;text-align:left;border-bottom:1px solid #dce3e5}.scroll{overflow:auto}select,input,summary{font:inherit;padding:10px;min-height:44px}input{max-width:85%}.note{border-left:4px solid #b37324;padding:12px 18px;background:#fff8e9}.muted{color:#566973}.kpi{font-size:25px;font-weight:650}.controls{display:flex;flex-wrap:wrap;gap:12px}article[hidden]{display:none}@media(max-width:600px){main{padding:16px 12px}section,article{padding:12px}table{font-size:13px}}
</style><main><p class="muted">2026-09-21 · 单候选 / 单种子 · 开发性验证 · 完整训练与封存测试尚未开启</p><h1>反馈恢复了失败样例；几何优化和经验迁移仍需分别验证</h1>
<p class="kpi">基准 71/78 → F3 77/78；F0 仍为 71/78</p><p>F3 恢复 6 个失败样例，原先成功的 71 对指标不变。F0 在共同成功样例上降低平均 CD/ECD，却没有恢复失败。当前证据支持两种修改各有收益，不能推出结构化反馈全面优于无反馈。</p>
<p class="note">'''+transfer_claim+''' 只有一个候选和一个种子，不能宣称统计显著、稳定高准确率或已证明递归自我改进。</p>
<section><h2>规范数据与使用边界</h2><p>全 562 对已按固定规则标准化：Zurich 真实 363 对 + PolyGNN mini 仿真 199 对。训练 432、封存 130；本轮仅使用其中 78 对。完整集只做预处理与往返核验，没有重建或反馈调用。</p><p>由输入包围盒计算中心与各向同性尺度，将对角线固定为 30；GT 仅跟随同一变换。无删点、无补点、无 GT 定义归一化。分析单位不是米，预测另存恢复源坐标的 OBJ。</p><p><a href="../../docs/DATASET_METHODS_V001.md">论文数据方法说明</a> · <a href="data_protocol_v001.json">机器可读筛选/预处理协议</a> · <a href="verification.json">坐标与渲染哈希核验</a></p></section>
<section><h2>隔离提议与共同起点</h2><p>78 对固定拆为 discovery24、selection24、transfer30。F0 与 F3 使用独立模型上下文、同一初始脚本和知识库，每组仅一次提议、最多 80 行差异、6 次工具调用。只有 F3 收到 discovery 外部诊断。模型不能执行评测或获取其余样例结果。</p><p>外层只用前 48 对的经验生成一份反馈排序与修改策略。迁移时，两策略重新载入完全相同的 v0.1.0，各获得相同 transfer30 基准证据、各提议一次。反馈内容相同、顺序与策略不同；这里的迁移是新开发任务，尚非未见城市测试。</p><p>累计 294 次重建尝试、4 次候选提议、1 次元策略提议。固定继承模型配置；提供方精确模型快照和 Token 无法取得，因此只匹配候选/工具预算，不宣称等 Token。批次耗时含外部评测，不能当纯推理速度。</p><p><a href="preregistration.json">预登记</a> · <a href="policy_evolved.json">演化策略与证据边界</a> · <a href="meta_experience.json">策略学习所用经验</a></p></section>
<section><h2>按来源报告的实际结果</h2><div class="scroll"><table><thead><tr><th>条件</th><th>来源</th><th>成功/尝试</th><th>拓扑通过/成功</th><th>共同成功 ΔCD ↓</th><th>共同成功 ΔECD ↓</th></tr></thead><tbody>'''+table+'''</tbody></table></div><p class="muted">前 3 个条件为全部 78 对；迁移条件仅 30 对，Δ 均相对同样本初始基准。失败计入分母；误差差值仅在共同成功样例上配对，不能用恢复后改变的成功样本均值判断进退。拓扑通过包括闭合、朝向、退化检查，未做完整预测自交检查。</p><img src="assets/paired_cd.svg" alt="真实与仿真分层的逐建筑CD变化，菱形为均值；F0均值下降，F3共同成功样例不变"><p><a href="per_building.csv">全部逐栋结果与分类 CSV</a> · <a href="summary.json">分区、分来源、配对差值与预算 JSON</a></p></section>
<section><h2>固定相机的逐栋对比</h2><p>首轮 F0、F3 是同一初始算法的平行候选，不是父子版本。每栋提供七视角和当前候选点云叠加，参考 Mesh 仅用于外部评测。失败处保留空位。图像点云最多约 5,000 点，评测仍使用全部点。</p><div class="controls"><label>实验 <select id="phase"><option value="first">首轮 78 对</option><option value="transfer">经验迁移 30 对</option></select></label><label>建筑筛选 <input id="query" placeholder="输入 ID 片段"></label></div><p id="count" aria-live="polite"></p><p>全批次总览：'''+ ' · '.join(f'<a href="assets/overview_{i}.jpg">第 {i} 页</a>' for i in range(1,7))+'''</p></section><div id="cards">'''+''.join(cards)+'''</div><section><h2>结论与下一步</h2><p>当前仍是可复现小试，尚未达到开启完整集合的条件。下一轮应分别检验失败恢复、轮廓贴合和两者组合，增加独立提议及随机种子，分析逐栋退化；演化策略须继续从同一起点验证收益，避免把历史候选收益当改进能力提升。</p><p>全部数值来自随附原始 JSON；CD/ECD 为欧氏距离、非平方、分析单位，NC 为双向法向绝对点积。没有官方 Overall 分数。GT 参与质量筛选会引入质量子集偏差，作者预训练划分存在重叠；不能据本轮宣称全分布或跨城泛化。</p></section></main><script>
const phase=document.querySelector('#phase'),query=document.querySelector('#query'),cards=[...document.querySelectorAll('article')];
function apply(save){let n=0;for(const c of cards){c.hidden=c.dataset.phase!==phase.value||!c.dataset.building.toLowerCase().includes(query.value.toLowerCase());if(!c.hidden)n++}document.querySelector('#count').textContent=`显示 ${n} 栋`;if(save){const u=new URL(location);u.searchParams.set('phase',phase.value);u.searchParams.set('q',query.value);history.replaceState(null,'',u)}}
function restore(){const p=new URL(location).searchParams;phase.value=p.get('phase')==='transfer'?'transfer':'first';query.value=p.get('q')||'';apply(false)}phase.addEventListener('change',()=>apply(true));query.addEventListener('input',()=>apply(true));addEventListener('popstate',restore);restore();
</script></html>'''
    (OUT/'index.html').write_text(page,encoding='utf-8')
    (OUT/'mini-brief.md').write_text('''# Report design contract
Analytical job: source-stratified paired comparison and failure accounting.
Route: OpenAI web data visualization → reports + statistical visualization.
Reading path: measured finding → limits → data method → protocol → paired results → all buildings.
Renderer: static Matplotlib SVG/PNG; Blender seven-view evidence; HTML table and filter.
Budget: 108 cards, images lazy-loaded, no network dependencies, no animation.
State: phase/query URL parameters; invalid phase resets; browser back restores; no local storage.
Mobile: single column, horizontal table only, explicit labels, native 44px controls, no hover-only values.
Colors: navy context, source-independent labeled F0/F3 marks, amber caution; values remain visible without color.
Fallback: JSON/CSV and static assets readable without JavaScript; all records remain in source.
QA: verify evaluator/source/render hashes and coordinate roundtrip; desktop/mobile browser and filter checks.
''',encoding='utf-8')
    # Each arm retains its own inference code, metadata, outputs, knowledge and external evidence.
    dependencies=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True)
    for arm in ARMS:
        dest=ROOT/'releases'/VERSIONS[arm]; dest.mkdir(exist_ok=False)
        shutil.copytree(WORK/arm/'source',dest/'source',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (dest/'source/requirements-lock.txt').write_text(dependencies,encoding='utf-8')
        (dest/'source/reproduce.py').write_text('''"""Replay this release with its frozen evaluator; no sealed samples allowed."""
import argparse, json, os, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--only');p.add_argument('--timeout',type=int,default=180)
a=p.parse_args();spec=json.loads((root.parent/'reports/inputs.json').read_text(encoding='utf-8'))
assert spec['role']=='development' and not spec.get('stage_locked')
out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
rows=[s for s in spec['samples'] if not a.only or s['id']==a.only]
assert rows, 'No matching samples'
results=[]
env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONUTF8':'1'}
for sample in rows:
    task=out/(sample['id']+'.task.json')
    task.write_text(json.dumps({'sample':sample,'source':str(root/'algorithm.py'),'output':str(out/'samples'/sample['id'])}),encoding='utf-8')
    try:
        r=subprocess.run([sys.executable,'-B','-m','harness.pilot_worker','--task',str(task)],cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=a.timeout)
        if r.returncode: raise RuntimeError(r.stderr)
        result=json.loads((out/'samples'/sample['id']/'result.json').read_text(encoding='utf-8'))
    except Exception as exc:result={'id':sample['id'],'status':'failed','error':str(exc)}
    results.append(result)
(out/'results.json').write_text(json.dumps({'samples':results},indent=2),encoding='utf-8')
''',encoding='utf-8')
        copy_file(ROOT/'config/data_protocol_v001.json',dest/'source/data_protocol_v001.json')
        copy_file(ROOT/'config/knowledge/rules.json',dest/'knowledge/rules.json')
        copy_file(WORK/arm/'inputs.json',dest/'reports/inputs.json')
        copy_file(WORK/arm/'results.json',dest/'reports/results.json')
        copy_file(WORK/'setup/preregistration.json',dest/'reports/preregistration.json')
        if arm!='baseline':
            part='all78' if arm in ['F0','F3'] else 'transfer_policy'
            write_json(dest/'reports/comparison.json',comparisons[part][arm])
            proposal=WORK/'proposals'/arm if arm in ['F0','F3'] else WORK/'transfer_proposals'/arm.split('_',1)[1]
            for file in ['feedback.json','proposal.json','policy.json']:
                if (proposal/file).exists():copy_file(proposal/file,dest/'feedback'/file)
        folder, role=('renders',{'baseline':'baseline','F0':'previous','F3':'current'}[arm]) if arm in ARMS[:3] else ('transfer_renders','previous' if arm==ARMS[3] else 'current')
        copy_file(WORK/folder/'render_manifest.json',dest/'renders/render_manifest.json')
        for row in rows[arm]:
            bid=row['id']
            if row['status']=='evaluated':
                for file in ['model.obj','model_source.obj','wireframe_source.obj','model.json']:
                    if (WORK/arm/'samples'/bid/file).exists():copy_file(WORK/arm/'samples'/bid/file,dest/'models'/bid/file)
                copy_file(WORK/arm/'samples'/bid/'models/input_model.json',dest/'models'/bid/'model.json')
                copy_file(WORK/arm/'samples'/bid/'adapter.json',dest/'reports/samples'/bid/'adapter.json')
                copy_file(WORK/arm/'samples'/bid/'evaluation.json',dest/'reports/samples'/bid/'evaluation.json')
            for view in ['oblique','opposite','top','front','back','left','right']:
                file=WORK/folder/f'{bid}_{view}_{role}.png'
                if file.exists():copy_file(file,dest/'renders'/file.name)
        (dest/'summary.md').write_text(f'''# {VERSIONS[arm]}
Condition: {arm}. Parent: exact v0.1.0 plus fixed input-only preprocessing.
Status: frozen experimental candidate, not a stable final algorithm.
Source OBJ is model_source.obj; model.obj is canonical analysis geometry, not source units.
Failures and all attempted IDs are retained in reports/results.json.
Seven-view cross-arm comparison: ../../reports/2026-09-21-starter78-feedback-pilot/index.html
Sibling arms must not be interpreted as successive algorithm parents.
Reproduce with `python source/reproduce.py --output NEW_ABSOLUTE_DIRECTORY [--only BUILDING_ID]` and source/requirements-lock.txt. Inputs retain the local standardized paths and hashes in reports/inputs.json. Only input path rebasing is needed on another machine; preserve file bytes and hashes.
''',encoding='utf-8')
        write_json(dest/'manifest.json',{'arm':arm,'version':VERSIONS[arm], 'not_official':True,
            'initial_source_sha256':raw['baseline']['source_sha256'], 'algorithm_sha256':raw[arm]['source_sha256'],
            'evaluator_sha256':raw[arm]['evaluator_sha256'],
            'files':{str(p.relative_to(dest)).replace('\\','/'):sha256(p) for p in sorted(dest.rglob('*')) if p.is_file()}})
    print(json.dumps({'report':str(OUT), 'releases':VERSIONS, 'verified_models':len(verification['roundtrips']),
                      'transfer':transfer},ensure_ascii=False),flush=True)


if __name__=='__main__': main()
