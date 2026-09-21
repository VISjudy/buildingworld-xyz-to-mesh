"""Evidence-based v002 report: component attribution, height audit and all 78 models."""
from pathlib import Path
import csv,html,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
WORK=ROOT/'work/experiments/2026-09-21/feedback-components-v002'
OLD=ROOT/'work/experiments/2026-09-21/starter78-feedback-pilot'
OUT=ROOT/'reports/2026-09-21-feedback-components-v002'
os.environ['MPLCONFIGDIR']=str(WORK/'matplotlib-report')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image,ImageDraw,ImageFont
from harness.io import read_json,write_json,sha256,read_obj
from harness.pilot_analysis import summarize,paired
from harness.preprocess import restore

RUNS={'baseline':OLD/'baseline','F0':OLD/'F0','F3':OLD/'F3',
      'T':WORK/'text_no_k_compat','TK':WORK/'text_k_compat','FULL':WORK/'full',
      'Hoff':WORK/'height_guard_off','v051':WORK/'v051_all78','Traw':WORK/'text_no_k'}
LABELS={'baseline':'初始 v0.1.0','F0':'旧 F0：凸轮廓','F3':'旧 F3：失败恢复',
        'T':'T：完整文本，无显式知识','TK':'TK：完整文本＋知识v2',
        'FULL':'FULL：综合文本＋知识＋图像','Hoff':'FULL关闭高度检查','v051':'历史 v0.5.1','Traw':'T原提议（API失败）'}
VERSIONS={'T':'v0.1.3-text-no-k-v002','TK':'v0.1.3-text-k-v002','FULL':'v0.1.3-full-feedback-v002',
          'Hoff':'v0.1.3-height-guard-off-v002','v051':'v0.5.1-starter78-comparison-v002','Traw':'v0.1.3-text-no-k-raw-v002'}
PROPOSALS={'T':'text_no_k_compat','TK':'text_k_compat','FULL':'full','Hoff':'height_guard_off','Traw':'text_no_k'}
ROLES={'baseline':'baseline','F0':'f0','F3':'f3','T':'text_no_k','TK':'text_k','FULL':'current','Hoff':'current','v051':'v051'}
CHANGES={
 'baseline':'固定60点/7.5%平面门槛、全局下包络、矩形轮廓、最低回波底面。没有本轮改进。',
 'F0':'仅把矩形替为稳健范围内点的凸包。收到8条知识，未收到结果反馈或图像。',
 'F3':'仅在屋顶拟合完全失败时增加同高点并降低支持门槛；原成功结果保持不变。只看结构化文本。',
 'T':'支持门槛改为max(12,2.5%)；增加法向/展布约束、空间均衡评分和凸轮廓。没有显式知识库或图像。',
 'TK':'增加失败后的自适应支持恢复、拟合展布检查和严格边界支持的凸轮廓；读取9条规则和2条经验，未看图。',
 'FULL':'支持门槛max(18,3%)、失败时12邻域法向恢复、空间均衡＋尾部残差评分、有限条件下凸包替换、相对临时底面的屋顶角点检查；实际查看2张诊断拼图。',
 'Hoff':'从FULL派生，只关闭相对临时底面的角点检查，用于精确算子消融。其他算子及参数不变。',
 'v051':'原归档脚本：保守噪声处理、alpha轮廓、局部屋面域/投票、多高度装配；没有注入本轮知识或反馈。',
 'Traw':'独立模型的原始T候选使用了当前NumPy不再支持的二维cross，78次均失败；原提议与失败全部保存。'}


def copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():raise FileExistsError(dst)
    shutil.copyfile(src,dst)


def build():
    OUT.mkdir(exist_ok=False);assets=OUT/'assets';assets.mkdir()
    spec=read_json(OLD/'setup/all78.json');samples={s['id']:s for s in spec['samples']}
    raw={a:read_json(p/'results.json')for a,p in RUNS.items()}
    rows={a:r['samples']for a,r in raw.items()};indexed={a:{r['id']:r for r in rs}for a,rs in rows.items()}
    partitions={n:{s['id']for s in read_json(OLD/'setup'/f'{n}.json')['samples']}for n in ['discovery','selection','transfer']}
    selection=lambda a,n:[r for r in rows[a]if r['id']in partitions[n]]
    pairs={'image_added':('TK','FULL'),'explicit_knowledge_added':('T','TK'),'height_guard_added':('Hoff','FULL'),
           'full_vs_initial':('baseline','FULL'),'full_vs_previous_F3':('F3','FULL'),'full_vs_F0':('F0','FULL'),
           'full_vs_v051':('v051','FULL')}
    comps={name:{'all78':paired(rows[a],rows[b]),'selection24':paired(selection(a,'selection'),selection(b,'selection'))}
           for name,(a,b)in pairs.items()}
    summary={'summaries':{a:summarize(rs)for a,rs in rows.items()},'comparisons':comps,
        'preregistration':read_json(WORK/'preregistration.json'),'new_batch_attempts':sum(len(rows[a])for a in VERSIONS),
        'extra_checks':'1 direct historical-v051 replay + 1 FULL Z-translation inference',
        'model_proposals':3,'deterministic_height_ablation':1,'compatibility_repairs':2,
        'old_results_reused_not_rerun':['baseline','F0','F3'],
        'limits':['Single candidate per model condition; causal modality/knowledge effects are not established.',
          'The no-knowledge condition still includes the model inherent prior knowledge.',
          'T and TK have documented algebraically equal NumPy API repairs; raw T failure is retained.',
          'All78 are development, selection24 is adaptive across project iterations; complete432/test130 remain locked.',
          'No complete self-intersection check; no official score; distance in canonical units, not metres.']}
    assert len({r['evaluator_sha256']for r in raw.values()})==1
    assert read_json(WORK/'proposals/text_k/feedback.json')==read_json(WORK/'proposals/full/feedback.json')==read_json(WORK/'proposals/text_no_k/feedback.json')
    assert sha256(WORK/'proposals/text_k/knowledge.json')==sha256(WORK/'proposals/full/knowledge.json')
    assert all(indexed['FULL'][bid]['mesh_sha256']==indexed['Hoff'][bid]['mesh_sha256']for bid in samples)
    write_json(OUT/'summary.json',summary)
    write_json(OUT/'model_catalog.json',{a:{'label':LABELS[a],'changes':CHANGES[a],'source_sha256':raw[a]['source_sha256'],
        'release':VERSIONS.get(a),'parent':'FULL' if a=='Hoff' else 'v0.1.0 same initial + fixed preprocessing' if a!='v051' else 'historical manual engineering',
        'images_used_for_proposal':a=='FULL','knowledge_version':'v002' if a in ['TK','FULL','Hoff']else 'v001'if a in ['F0','F3']else None}for a in RUNS})
    for name in ['feedback-v002.json','knowledge-v002.json','preregistration.json','height_guard_ablation_protocol.json']:
        copy(WORK/name,OUT/name)
    for a,p in RUNS.items():copy(p/'results.json',OUT/f'{a}_results.json')
    for name in ['summary.json','per_building.csv','findings.md']:
        copy(WORK/'height-audit'/name,OUT/'height-audit'/name)
    copy(WORK/'height-translation-check/verification.json',OUT/'height-translation-check.json')
    copy(WORK/'v051_all78_freeze/provenance.json',OUT/'v051-provenance.json')
    copy(WORK/'v051_direct_verify/verification.json',OUT/'v051-direct-replay.json')
    for a,p in PROPOSALS.items():
        for name in ['proposal.json','compatibility.json','image_manifest.json']:
            if (WORK/'proposals'/p/name).exists():copy(WORK/'proposals'/p/name,OUT/'proposals'/a/name)
    for i in [1,2]:copy(WORK/f'discovery-evidence-{i}.png',OUT/f'discovery-evidence-{i}.png')
    # Frozen artifacts: successful output is not equivalent to topology accepted.
    deps=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True)
    verified=[];render_manifest=read_json(WORK/'renders/render_manifest.json')
    render_index={r['id']:r for r in render_manifest['samples']}
    for a,version in VERSIONS.items():
        dest=ROOT/'releases'/version;dest.mkdir(exist_ok=False)
        shutil.copytree(RUNS[a]/'source',dest/'source',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (dest/'source/requirements-lock.txt').write_text(deps,encoding='utf-8')
        copy(ROOT/'releases/v0.1.2-pilot-f3-v001/source/reproduce.py',dest/'source/reproduce.py')
        copy(ROOT/'config/data_protocol_v001.json',dest/'source/data_protocol_v001.json')
        for name in ['results.json','inputs.json']:copy(RUNS[a]/name,dest/'reports'/name)
        if a in PROPOSALS:
            p=WORK/'proposals'/PROPOSALS[a]
            for name in ['knowledge.json','feedback.json','proposal.json','compatibility.json','image_manifest.json']:
                if (p/name).exists():copy(p/name,dest/('knowledge'if name=='knowledge.json'else 'feedback')/name)
            if a in ['T','TK']:
                orig='text_no_k'if a=='T'else 'text_k'
                copy(WORK/'proposals'/orig/'candidate.py',dest/'source/original_candidate.py')
        if a=='v051':
            copy(ROOT/'releases/v0.5.1-batch02/source/pointcloud_to_mesh.py',dest/'source/historical_pointcloud_to_mesh.py')
            copy(OUT/'v051-provenance.json',dest/'reports/provenance.json')
        for row in rows[a]:
            bid=row['id'];folder=RUNS[a]/'samples'/bid
            if row['status']!='evaluated':continue
            model=read_obj(folder/'model.obj');source=read_obj(folder/'model_source.obj');t=read_json(samples[bid]['transform'])
            error=float(np.abs(source['vertices']-restore(model['vertices'],t['origin'],t['scale'])).max())
            assert error<=1e-5 and model['faces']==source['faces']
            assert sha256(folder/'model.obj')==row['mesh_sha256']==render_index[bid]['source_hashes'][ROLES[a]]
            verified.append({'arm':a,'id':bid,'source_coordinate_max_error':error,'render_hash_verified':True})
            for name in ['model.obj','model_source.obj','wireframe_source.obj']:copy(folder/name,dest/'models'/bid/name)
            for name in ['evaluation.json','adapter.json']:copy(folder/name,dest/'reports/samples'/bid/name)
            candidate_json=folder/'models'/('input_lod2.json'if a=='v051'else 'input_model.json')
            copy(candidate_json,dest/'models'/bid/'model.json')
            for view in ['oblique','opposite','top','front','back','left','right']:
                name=f'{bid}_{view}_{ROLES[a]}.png';copy(WORK/'renders'/name,dest/'renders'/name)
        write_json(dest/'renders/provenance.json',{'same_camera_all_conditions':True,'source':'work/experiments/2026-09-21/feedback-components-v002/renders/render_manifest.json',
            'height_guard_off_reuses_identical_FULL_geometry':a=='Hoff'})
        (dest/'summary.md').write_text(f'''# {version}
{LABELS[a]}。{CHANGES[a]}
Frozen experimental output; inspect topology and regressions, not merely exported-file count.
Run `python source/reproduce.py --output NEW_ABSOLUTE_PATH [--only ID]` with requirements-lock.txt and local standardized inputs.
model_source.obj / wireframe_source.obj retain source coordinates; model.obj is canonical analysis geometry.
Report: ../../reports/2026-09-21-feedback-components-v002/index.html
''',encoding='utf-8')
        write_json(dest/'manifest.json',{'version':version,'arm':a,'algorithm_sha256':raw[a]['source_sha256'],'evaluator_sha256':raw[a]['evaluator_sha256'],
            'files':{str(p.relative_to(dest)).replace('\\','/'):sha256(p)for p in sorted(dest.rglob('*'))if p.is_file()}})
    write_json(OUT/'verification.json',{'evaluated_outputs_checked':len(verified),'models':verified,'same_evaluator':True,
        'same_text_evidence_for_new_conditions':True,'same_K_for_TK_and_FULL':True,'FULL_Hoff_all78_byte_identical':True})
    flat=[]
    for a,rs in rows.items():
        for r in rs:
            b=indexed['baseline'][r['id']];prev=indexed['F3'][r['id']]
            item={'arm':a,'id':r['id'],'source':r['stratum'],'status':r['status'],'topology_pass':r.get('topology_pass'),
                  **{k:r.get(k)for k in ['CD','ECD','NC','p95','seconds']}}
            for reference,label in [(b,'initial'),(prev,'previous_F3')]:
                for metric in ['CD','ECD','NC','p95']:
                    item[f'delta_{metric}_vs_{label}']=r[metric]-reference[metric]if r['status']==reference['status']=='evaluated'else None
            flat.append(item)
    with (OUT/'per_building.csv').open('x',encoding='utf-8-sig',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18);cards=[];thumbs=[]
    views=['oblique','opposite','top','front','back','left','right']
    for bid,s in samples.items():
        for mode,columns in [('main',[('input','Input'),('baseline','Initial v0.1.0'),('f0','F0: footprint'),('f3','F3: recovery'),('current','FULL: all implemented'),('v051','Historical v0.5.1'),('reference','Reference mesh')]),
                             ('ablation',[('input','Input'),('text_no_k','T: text, no explicit K'),('text_k','TK: text + K v2'),('current','FULL: text + K + image'),('reference','Reference mesh'),('overlay','FULL + points')])]:
            for view in views:
                canvas=Image.new('RGB',(320*len(columns),320),'#edf2f4');draw=ImageDraw.Draw(canvas)
                for col,(role,label)in enumerate(columns):
                    draw.text((col*320+7,8),label,font=font,fill='#21333f');src=WORK/'renders'/f'{bid}_{view}_{role}.png'
                    if src.exists():canvas.paste(Image.open(src).convert('RGB'),(col*320,40))
                    else:draw.text((col*320+40,170),'FAILED / no evaluated mesh',font=font,fill='#a73528')
                canvas.save(assets/f'{mode}_{bid}_{view}.jpg',quality=84)
                if mode=='main'and view=='oblique':thumbs.append((bid,canvas.resize((1120,160))))
        case_rows=''
        for a in ['baseline','F0','F3','T','TK','FULL','v051']:
            r=indexed[a][bid]
            values=''.join(f'<td>{r[k]:.4f}</td>'for k in ['CD','ECD','NC','p95'])if r['status']=='evaluated'else '<td colspan="4">失败，保留记录</td>'
            topology='通过'if r.get('topology_pass')else '未通过'if r['status']=='evaluated'else '—'
            case_rows+=f'<tr><th>{LABELS[a]}</th>{values}<td>{topology}</td></tr>'
        options=''.join(f'<option value="{a}">{LABELS[a]}</option>'for a in ['baseline','F0','F3','T','TK','FULL','v051'])
        historical_link=(f'<a href="../../releases/{VERSIONS["v051"]}/models/{bid}/model_source.obj">v0.5.1源坐标OBJ</a>' if indexed['v051'][bid]['status']=='evaluated' else '<span>v0.5.1重建失败：没有OBJ，详见本栋指标及失败记录</span>')
        cards.append(f'''<article data-id="{bid}" data-source="{s['evaluation_stratum']}"><h3>{bid}</h3><p>{s['evaluation_stratum']} · 同一相机、输入、评测器；FULL 是本轮综合候选。</p><div class="pan"><img loading="lazy" data-comparison src="assets/main_{bid}_oblique.jpg" alt="{bid} 输入、初始、F0、F3、综合候选、历史v051、参考同视角比较"></div><details><summary>逐版本指标与我的评价</summary><div class="scroll"><table><tr><th>版本</th><th>CD ↓</th><th>ECD ↓</th><th>NC ↑</th><th>点到面P95 ↓</th><th>拓扑</th></tr>{case_rows}</table></div><label>本栋更认可的版本 <select data-rating><option value="">尚未评价</option>{options}<option value="none">都不好</option></select></label><label>原因 / 屋顶、轮廓、立面问题<textarea data-comment rows="2" placeholder="例如：FULL屋顶更贴合，但立面仍太短"></textarea></label><p><a href="../../releases/{VERSIONS['FULL']}/models/{bid}/model_source.obj">FULL源坐标OBJ</a> · {historical_link}</p></details></article>''')
    for page in range(0,len(thumbs),13):
        sheet=Image.new('RGB',(1120,13*186),'white');draw=ImageDraw.Draw(sheet)
        for j,(bid,im)in enumerate(thumbs[page:page+13]):draw.text((5,j*186),bid,font=font,fill='#20333f');sheet.paste(im,(0,j*186+24))
        sheet.save(assets/f'overview_{page//13+1}.jpg',quality=84)
    table=''
    for a in ['baseline','F0','F3','T','TK','FULL','Hoff','v051','Traw']:
        for source,g in summary['summaries'][a].items():
            m=g['mean_success_only_not_used_for_paired_claim'];nums=''.join(f'<td>{m[k]:.4f}</td>'if m[k]is not None else '<td>—</td>'for k in ['CD','ECD','NC'])
            table+=f'<tr><th>{LABELS[a]}</th><td>{source}</td><td>{g["success"]}/{g["attempted"]}</td><td>{g["topology_pass"]}/{g["attempted"]}</td>{nums}</tr>'
    contribution_rows=''
    for name,label in [('explicit_knowledge_added','加入显式知识 T→TK'),('image_added','加入图像 TK→FULL'),('height_guard_added','启用高度检查 Hoff→FULL')]:
        for source,r in comps[name]['all78']['by_source'].items():
            d=r['paired_mean_delta'];contribution_rows+=f'<tr><th>{label}</th><td>{source}</td><td>{r["common_success"]}</td><td>{d["CD"]:+.5f}</td><td>{d["ECD"]:+.5f}</td><td>{r["recovered"]} / {r["new_failures"]}</td></tr>'
    catalog=''.join(f'<details class="catalog"><summary>{LABELS[a]}</summary><p>{CHANGES[a]}</p><p>代码 SHA256：<code>{raw[a]["source_sha256"]}</code></p></details>'for a in ['baseline','F0','F3','T','TK','FULL','Hoff','v051'])
    # Paired modality candidate comparison: matched successful population, separated sources.
    fig,axes=plt.subplots(1,2,figsize=(10,3.6),layout='constrained')
    for ax,source in zip(axes,['real_zurich','synthetic_mini']):
        sub=[r for r in rows['FULL']if r['stratum']==source];d=[r['CD']-indexed['TK'][r['id']]['CD']for r in sub]
        ax.scatter(range(len(d)),d,s=20,color='#127482');ax.axhline(0,color='#888',lw=1)
        ax.set_title(f'{source}: mean delta {np.mean(d):+.4f}');ax.set_xlabel('Building (fixed ID order)');ax.set_ylabel('CD(FULL) - CD(TK)');ax.grid(axis='y',alpha=.2)
    fig.savefig(assets/'image_condition_delta.svg');fig.savefig(assets/'image_condition_delta.png',dpi=150);plt.close(fig)
    html_start='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>反馈贡献、算法改动与高度规则 · v002</title><style>
body{margin:0;background:#f3f5f5;color:#203541;font:16px/1.75 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1240px;margin:auto;padding:30px 20px}h1{font-size:clamp(27px,4vw,41px);line-height:1.3}h2{font-size:25px;margin-top:20px}h3{font-size:17px;overflow-wrap:anywhere}section,article{background:white;padding:22px;border:1px solid #dce3e5;border-radius:8px;margin:18px 0}a{color:#076475}table{border-collapse:collapse;width:100%;font-size:14px;white-space:nowrap}td,th{border-bottom:1px solid #dce3e5;padding:9px;text-align:left}.scroll,.pan{overflow:auto}.pan img{width:2240px;max-width:none}.ablation .pan img{width:1920px}img{max-width:100%;height:auto}code{overflow-wrap:anywhere;white-space:normal}select,button,input,summary,textarea{font:inherit;min-height:44px;padding:8px;box-sizing:border-box}textarea{display:block;width:100%}label{display:inline-block;max-width:100%;margin:8px 10px 8px 0}input{max-width:90%}.note{border-left:4px solid #b57623;background:#fff6e5;padding:14px 18px}.catalog{border-bottom:1px solid #dce3e5}.muted{color:#546875}.controls{display:flex;flex-wrap:wrap;gap:10px}article[hidden]{display:none}@media(max-width:600px){main{padding:14px 10px}section,article{padding:12px}h2{font-size:22px}}
</style><main><p class="muted">2026-09-21 · v002 · 同一固定78对 · 新增468次批次尝试 · 非官方评测</p><h1>先说明每版改了什么，再看模型与反馈贡献</h1><p><strong>FULL 综合候选：78/78 有可评测输出，78/78 通过当前拓扑检查。</strong>本轮文本＋知识候选也是78/78；综合候选的平均几何误差更低。历史v0.5.1为76/78有输出、28/78拓扑通过。成功输出数量不等于几何正确。</p><p class="note">本轮新增的是单候选对照：图像条件的候选更好，不足以将全部收益因果归于图像。知识、反馈内容和模型修改策略需要重复提议验证。高度检查开关在78栋上的模型字节完全一致，当前可测贡献为0。</p>
<section><h2>1. 知识库、反馈与演化：原来做了什么</h2><p>初始知识库为8条JSON规则：K01观测轮廓，K02平面局部支持与附楼，K03缺失点不等于空白，K04闭合与一致装配，K05正交/竖墙软先验，K06全点误差与失败保留，K07排除共面三角化边，K08最低回波不唯一决定地面。每条记录出处、条件、反例、算子和状态，属于初步规则库。</p><p><strong>上轮F0与F3的知识库完全相同。</strong>外层生成了4条经验、改变反馈排序和提议策略，但没有更新8条建筑规则。上轮所有渲染均用于事后展示，模型未收到图像，因此上轮图像反馈贡献为“未测”。原始/演化策略迁移同为26/30，不能称已证明自我进化。</p><p>本轮知识v2保留8条规则，增加K09“屋顶标高与离地高度分离”和X01/X02两条经验。更新过程有审计依据，尚无经验证的自动知识晋级机制。本轮不再次声称完成递归迁移证明。</p><p><a href="../../docs/FEEDBACK_COMPONENTS_V002.md">逐项方法说明</a> · <a href="knowledge-v002.json">知识v2原文</a> · <a href="../2026-09-21-starter78-feedback-pilot/index.html">保留的上轮报告</a></p></section>
<section><h2>2. 本轮给模型的反馈，与仍未完成的消融</h2><div class="scroll"><table><tr><th>证据层</th><th>本轮实际提供</th><th>限制 / 逐项去除实验</th></tr><tr><td>观测贴合</td><td>全点距离、P95、覆盖率、局部点/面位置</td><td>已进入反馈；单独去除尚未运行</td></tr><tr><td>方向</td><td>PCA稳定点比例、法向代理、GT NC</td><td>置信度是代理；去除方向尚未运行</td></tr><tr><td>结构边</td><td>ECD、GT边中点与最近预测边位置、边ID</td><td>局部中点诊断；去除结构尚未运行</td></tr><tr><td>拓扑</td><td>开放边、非流形边、朝向、退化</td><td>完整自交检测尚未实现</td></tr><tr><td>建筑规则</td><td>屋顶候选点数/支持门槛、基底来源、规则条件</td><td>知识开关已测；各规则逐条消融尚未运行</td></tr><tr><td>参考真值</td><td>开发集CD/ECD/NC、GT上下标高</td><td>只在开发反馈使用，推理禁止GT</td></tr><tr><td>图像</td><td>2张固定相机拼图：输入/初始/GT/顶视</td><td>FULL实际查看；深度/法向栅格与自适应裁剪尚未实现</td></tr></table></div><p>相较上轮，反馈由少量案例摘要扩充为discovery24逐栋六层证据，新增支持数量、法向可靠性代理、结构边定位与高程来源。全部文本三组相同；TK与FULL知识文件相同；只有FULL拿到两张图。</p><p><a href="feedback-v002.json">实际反馈包</a> · <a href="discovery-evidence-1.png">模型实际查看的图1</a> · <a href="discovery-evidence-2.png">图2</a> · <a href="proposals/FULL/proposal.json">FULL看图记录与逐项修改</a></p><p>FULL表示综合<strong>本轮已经实现</strong>的反馈，仍不包含表中未实现项。图像辅助离线代码修改，最终重建只用XYZ。</p></section>
<section><h2>3. 各版本具体改动</h2>'''
    body=html_start+catalog+'''<p class="note">T原始候选因NumPy 2.5.3拒绝二维cross而78次失败；T和TK分别做了1处/2处等价行列式替换，未改几何阈值。原提议和兼容版均保存；不要将API修复收益算作知识贡献。v0.5.1使用Git归档原字节和原默认保守噪声处理，外部指标仍计算全部输入点。</p></section>
<section><h2>4. 结果与消融贡献</h2><div class="scroll"><table><tr><th>条件</th><th>来源</th><th>有输出/总数</th><th>拓扑通过/总数</th><th>CD ↓</th><th>ECD ↓</th><th>NC ↑</th></tr>'''+table+'''</table></div><p>上表均值只覆盖成功输出，不能跨不同成功分母直接推断进退。下表采用共同成功样例配对，并单列恢复/新增失败；真实与仿真分别报告，单位为分析坐标，不是米。</p><div class="scroll"><table><tr><th>对照</th><th>来源</th><th>共同成功数</th><th>ΔCD ↓</th><th>ΔECD ↓</th><th>恢复 / 新失败</th></tr>'''+contribution_rows+'''</table></div><img src="assets/image_condition_delta.svg" alt="图像条件相对完整文本加知识条件的逐栋CD变化，按来源分开；单次候选差异不构成图像因果证明"><p>知识条件的修改更保守，增加恢复和有效拓扑但几何误差存在取舍。图像条件本次降低两来源平均误差，但部分建筑仍可能退化。高度检查无可测变化。详细selection24结果、全部逐栋差值、旧版/FULL/v0.5.1配对均在 <a href="summary.json">summary.json</a> 与 <a href="per_building.csv">CSV</a>。</p></section>
<section><h2>5. Z值能不能直接作为建筑高度</h2><p><strong>Z是标高坐标；建筑或某处立面高度 = 屋顶标高 − 可信基底标高。</strong>本数据的分析坐标零点是输入包围盒中心，不能当作地面。Zurich还原后的底面源Z约401–600，但建筑总高约0.5–18.5源单位，不能用绝对Z的大小判断建筑高度合理性。</p><p>真实38栋中37栋的最低回波高于参考底面超过2%参考建筑高度；最低回波的底高绝对误差中位数37.75%。仿真40栋相应误差中位数1.51%。屋顶q99端点误差中位数分别约2.95%和1.35%。这支持“屋顶标高有信息”，不支持“最低点就是真地面”或“屋顶Z就是立面高度”。参考Mesh底面也未保证是现场可见地面。</p><p>异常检测应基于局部稳定屋面支持、相对残差/尺度及坐标来源；异常修正应退回原有有依据的拟合并保留不确定性，不能拿绝对Z阈值或canonical零点截断。本轮FULL只检查屋顶角点是否低于临时底面：可行时重选有支持平面，否则明确失败；没有实现任意坏Z自动恢复真实高度。2%/5%是审计误差带，未学成部署阈值。</p><p>关闭这条检查，78栋模型与FULL逐字节相同，故当前贡献为0。将一栋输入整体上移500分析单位，输出等量上移且拓扑不变（单例回归验证）。</p><p><a href="height-audit/findings.md">高度审核与反例</a> · <a href="height-audit/per_building.csv">78栋高度数据</a> · <a href="height-translation-check.json">平移验证</a></p></section>
<section><h2>6. 逐栋同视角对比与反馈</h2><p>主线排列：输入｜v0.1.0｜F0轮廓｜F3恢复｜FULL综合｜历史v0.5.1｜参考。消融排列：输入｜T无显式知识｜TK文本知识｜FULL加入图像｜参考｜叠加。向右滚动查看完整排列，切换七个固定视角；失败保留空位。</p><div class="controls"><label>排列 <select id="mode"><option value="main">主线与v0.5.1</option><option value="ablation">知识/图像消融</option></select></label><label>视角 <select id="view">'''+''.join(f'<option value="{v}">{v}</option>'for v in views)+'''</select></label><label>建筑 <input id="query" placeholder="ID片段"></label><button id="export">下载我的逐栋评价JSON</button></div><p id="count" aria-live="polite"></p><p>评价只保存在本机浏览器；下载后可交给后续迭代，不会自动变成训练标签或评测真值。</p><p>全批次总览：'''+ ' · '.join(f'<a href="assets/overview_{i}.jpg">{i}</a>'for i in range(1,7))+'''</p></section>'''+''.join(cards)+'''<section><h2>可复现性与后续</h2><p>三个独立提议均从同一v0.1.0出发，最多140变更行、10次工具调用、1次语法检查；同继承模型但精确服务快照/Token不可得。只给discovery24证据，selection24另报，但全部78属于持续开发集。完整432/130仍锁定。本轮没有证明递归改进，也没有完成计划中F0–F5、E1–E10全矩阵。</p><p>6个新冻结目录保存源码、依赖、知识、反馈、源坐标模型、失败和七视角；旧报告/旧版本未覆盖。<a href="verification.json">往返/渲染哈希</a> · <a href="model_catalog.json">版本来源目录</a> · <a href="v051-provenance.json">v0.5.1原字节证据</a>。78/78当前拓扑通过仍不代表高准确率；下一轮应处理真实组缺失底面证据、复杂多高度结构与逐栋退化，再决定完整集阶段切换。</p></section></main><script>
const cards=[...document.querySelectorAll('article')],mode=document.querySelector('#mode'),view=document.querySelector('#view'),query=document.querySelector('#query');
const key='lod2-feedback-components-v002-reviews';let reviews={};try{reviews=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){}
function apply(save){let n=0;document.body.classList.toggle('ablation',mode.value==='ablation');for(const c of cards){c.hidden=!c.dataset.id.toLowerCase().includes(query.value.toLowerCase());if(!c.hidden)n++;c.querySelector('[data-comparison]').src=`assets/${mode.value}_${c.dataset.id}_${view.value}.jpg`}document.querySelector('#count').textContent=`显示 ${n} / 78 栋`;if(save){const u=new URL(location);for(const [k,v]of Object.entries({mode:mode.value,view:view.value,q:query.value}))u.searchParams.set(k,v);history.replaceState(null,'',u)}}
function restore(){const p=new URL(location).searchParams;mode.value=p.get('mode')==='ablation'?'ablation':'main';view.value=['oblique','opposite','top','front','back','left','right'].includes(p.get('view'))?p.get('view'):'oblique';query.value=p.get('q')||'';apply(false)}
for(const c of cards){const id=c.dataset.id,s=c.querySelector('[data-rating]'),t=c.querySelector('[data-comment]');s.value=reviews[id]?.preferred||'';t.value=reviews[id]?.comment||'';const store=()=>{reviews[id]={preferred:s.value,comment:t.value};try{localStorage.setItem(key,JSON.stringify(reviews))}catch(e){}};s.addEventListener('change',store);t.addEventListener('input',store)}
for(const el of [mode,view,query])el.addEventListener(el===query?'input':'change',()=>apply(true));addEventListener('popstate',restore);restore();
document.querySelector('#export').onclick=()=>{const blob=new Blob([JSON.stringify({report:'feedback-components-v002',status:'human_feedback_not_ground_truth',reviews},null,2)],{type:'application/json'});const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download='building-model-reviews-v002.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};
</script></html>'''
    (OUT/'index.html').write_text(body,encoding='utf-8')
    (OUT/'mini-brief.md').write_text('''# Visualization contract
Route: OpenAI web data visualization → reports / statistical comparison. Standard explanatory report, same established visual style.
Layer 1: method catalog and evidence matrix, semantic HTML tables/details; goal identify exactly what changed. Local specialist pass.
Layer 2: source-stratified paired CD dot plot, Matplotlib SVG+PNG, zero line and mean direct label; no invented confidence interval. Local statistical pass.
Layer 3: seven-view Blender comparisons, same per-building camera/material across versions, source hashes checked. Dedicated visual review.
Layer 4: height audit, tabular precise values + linked full CSV, distinguish coordinate and relative height. Independently audited by height_audit agent.
State: URL-backed mode/view/query with safe defaults, browser history restore. Reviews localStorage only, explicit JSON export, not automatic training evidence.
Mobile: horizontally scrollable comparison strip and tables; no document overflow; labels, alt text, native controls >=44px. No hover-only facts.
Fallback: all CSV/JSON/OBJ assets independent of JavaScript; initial comparison images in HTML. No network dependencies or animation.
QA: render/evaluation hash parity, source coordinate reimport, common evaluator/feedback/knowledge checks, desktop/mobile browser, view switching, URL restore and feedback export.
''',encoding='utf-8')
    print(json.dumps({'report':str(OUT),'verified_outputs':len(verified),'new_attempts':summary['new_batch_attempts'],'comparisons':{k:v['all78']for k,v in comps.items()}},ensure_ascii=False),flush=True)


if __name__=='__main__':build()
