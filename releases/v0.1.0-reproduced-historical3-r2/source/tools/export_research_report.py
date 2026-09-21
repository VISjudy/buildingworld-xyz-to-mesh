"""Evidence-only offline HTML stage report, regenerated into a NEW output folder."""
import argparse
from collections import Counter
import html
import json
from pathlib import Path
import shutil
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from harness.io import read_json,write_json,read_obj,read_points,sha256
from harness.evaluate import prepare,closest


def build(experiment, derived, output):
    b=Path(experiment);out=Path(output);out.mkdir(parents=True,exist_ok=False)
    assets=out/'assets';assets.mkdir()
    rows=read_json(b/'candidate001-dev20/decision.json')['comparison']['samples']
    spec=read_json(b/'setup/development20.json');inputs={s['id']:s for s in spec['samples']}
    renders=b/'candidate001-dev20/renders-v002'
    rm=read_json(renders/'render_manifest.json')
    for rec in rm['samples']:
        for key,run in [('baseline','baseline-dev20'),('previous','baseline-dev20'),('current','candidate001-dev20')]:
            mesh=b/run/'samples'/rec['id']/'model.obj'
            if mesh.is_file():
                assert rec['source_hashes'][key]==read_json(mesh.parent/'evaluation.json')['mesh_sha256']
    labels={'improved':'改善','unchanged':'持平','regressed':'退化','failed':'失败'}
    counts=Counter(r['classification'] for r in rows)
    fig,ax=plt.subplots(figsize=(10,6),layout='constrained')
    for y,row in enumerate(rows):
        bv=row['baseline']['p95'];cv=row['current'].get('p95')
        if cv is not None:
            ax.plot([bv,cv],[y,y],color='#98a5ad',lw=2)
            ax.scatter(cv,y,color='#be4b3e' if row['classification']=='regressed' else '#087f8c',marker='s',s=28)
        else:ax.text(bv+.15,y,'FAILED',va='center',color='#be4b3e',fontsize=8)
        ax.scatter(bv,y,facecolors='white',edgecolors='#263f50',s=38,zorder=3)
    ax.set_yticks(range(len(rows)),[r['id'] for r in rows]);ax.invert_yaxis()
    ax.set_xlabel('All-point to mesh P95 (source units; lower is better)')
    ax.set_title('20 development buildings | circle: baseline, square: candidate')
    ax.grid(axis='x',alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.savefig(assets/'paired_p95.svg');fig.savefig(assets/'paired_p95.png',dpi=160);plt.close(fig)
    cards=[];thumbs=[]
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    for row in rows:
        bid=row['id'];canvas=Image.new('RGB',(1920,470),'#eff3f5');draw=ImageDraw.Draw(canvas)
        for col,(key,title) in enumerate([('input','Input cloud'),('baseline','v0.1.0 baseline'),('previous','Previous = baseline'),('current','Candidate 001')]):
            draw.text((col*480+16,12),title,fill='#18313e',font=font)
            src=renders/f'{bid}_oblique_{key}.png'
            if src.exists():canvas.paste(Image.open(src).convert('RGB'),(col*480,45))
            else:draw.text((col*480+90,210),'FAILED - no mesh',fill='#a93028',font=font)
        canvas.save(assets/f'{bid}_comparison.png')
        thumbs.append(canvas.resize((960,235)))
        # Identical residual scale and input points across versions. No denoising for score.
        p=read_points(inputs[bid]['points']);origin=p.mean(0)
        fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
        scatter=None
        for ax,run,title in zip(axes,['baseline-dev20','candidate001-dev20'],['Baseline','Candidate 001']):
            mesh=b/run/'samples'/bid/'model.obj'
            if mesh.exists():
                m,_,o=prepare(read_obj(mesh));dist,_=closest(m,p-o)
                scatter=ax.scatter(p[:,0]-origin[0],p[:,1]-origin[1],c=dist,s=3,cmap='magma',vmin=0,vmax=10)
            else:ax.text(.5,.5,'FAILED',transform=ax.transAxes,ha='center')
            ax.set_title(title);ax.set_aspect('equal');ax.set_xlabel('X - display origin');ax.set_ylabel('Y - display origin')
            ax.set_xlim(p[:,0].min()-origin[0]-.5,p[:,0].max()-origin[0]+.5)
            ax.set_ylim(p[:,1].min()-origin[1]-.5,p[:,1].max()-origin[1]+.5)
        fig.colorbar(scatter,ax=axes,label='Point-to-surface distance (source units; display capped at 10)')
        fig.savefig(assets/f'{bid}_residual.png',dpi=125);plt.close(fig)
        val=lambda v:'NA' if v is None else f'{v:.6f}'
        cards.append(f'''<article id="b{bid}"><h3>{bid} · {labels[row['classification']]}</h3>
        <p>P95 基准 {val(row['baseline'].get('p95'))} → 当前 {val(row['current'].get('p95'))}；相对基准 / 上一版差值均为 {val(row['delta_previous'])}。</p>
        <a href="assets/{bid}_comparison.png"><img src="assets/{bid}_comparison.png" alt="建筑 {bid}：输入、基准、上一版、当前版同相机渲染"></a>
        <details><summary>查看全部输入点残差（统一色标）</summary><img loading="lazy" src="assets/{bid}_residual.png" alt="建筑 {bid} 基准和当前点面残差顶视图，非完整轮廓真值"></details></article>''')
    overview=Image.new('RGB',(1920,235*10),'white')
    for i,im in enumerate(thumbs):overview.paste(im,((i%2)*960,(i//2)*235))
    overview.save(assets/'overview.png')
    dm=read_json(Path(derived)/'dataset_manifest.json');qa=read_json(Path(derived)/'blender_qa.json')
    passed=[s['id'] for s in qa['samples'] if s['provisional_training_eligible']]
    dataset_counts=Counter(s['status'] for s in dm['samples'])
    data={'experiment':'lod2-rsi-v001','status':'candidate_not_promoted','classification_counts':dict(counts),'samples':rows,
          'dataset':{'paired':len(dm['samples']),'counts':dict(dataset_counts),'geometry_filter_passed':passed},
          'official_score':None,'independent_test':False,'formal_rsi_experiment':False}
    write_json(out/'data.json',data)
    qa_copy={k:v for k,v in qa.items() if k!='source_root'};write_json(out/'derived_qa.json',qa_copy)
    table=''.join(f"<tr><td><a href='#b{r['id']}'>{r['id']}</a></td><td>{r['baseline']['p95']:.6f}</td><td>{'NA' if r['current'].get('p95') is None else format(r['current']['p95'],'.6f')}</td><td>{labels[r['classification']]}</td></tr>" for r in rows)
    doc=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>LoD2 RSI · 第一阶段实验记录</title><style>
    *{{box-sizing:border-box}}body{{margin:0;background:#f3f6f8;color:#18313e;font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}}
    main{{max-width:1160px;margin:auto;padding:40px 24px}}h1{{font-size:36px;line-height:1.25}}h2{{margin-top:48px}}h3{{margin:0}}a{{color:#006a81}}a:focus,summary:focus{{outline:3px solid #db7900}}
    .note{{border-left:4px solid #d08123;background:#fff5e4;padding:18px}}.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.stats div,article{{background:white;padding:20px;border:1px solid #dce4e8;border-radius:8px}}.stats strong{{display:block;font-size:30px}}article{{margin:24px 0}}img{{width:100%;height:auto}}table{{width:100%;border-collapse:collapse;background:#fff}}th,td{{text-align:left;padding:8px;border-bottom:1px solid #dce4e8}}small{{color:#536772}}summary{{cursor:pointer}}@media(max-width:600px){{main{{padding:20px 12px}}h1{{font-size:28px}}.stats{{grid-template-columns:repeat(2,1fr)}}article{{padding:12px}}table{{font-size:13px}}}}@media print{{details{{display:block}}article{{break-inside:avoid}}}}</style>
    <main><small>2026-09-21 · LoD2 / 外部证据与版本复现 · OpenAI data visualization 技能工作流</small>
    <h1>凹轮廓修改有局部收益，<br>第一轮候选未通过验收</h1>
    <p>保持 v0.1.0 屋面拟合不变，仅将凸包轮廓替换为固定参数的凹包。这次实验用于验证反馈、复测和冻结流程。</p>
    <div class="stats">{''.join(f'<div>{labels[k]}<strong>{counts[k]} / 20</strong></div>' for k in ['improved','unchanged','regressed','failed'])}</div>
    <p class="note">20 栋来自用户授权使用的测试点云目录，现作为开发数据；不是封存测试集，也不是历史训练 20 栋。结果为全部输入点到 Mesh 的 P95，单位沿用源数据，未核实为米。官方 CD/ECD/NC 未取得。1 栋失败不以 0 计分。</p>
    <h2>每栋的收益与退化必须一起看</h2><p>空心圆为基准，方块为候选。颜色之外同时使用形状与文字；建筑 2124 构建失败，未产生当前模型。P95 不能判断未观测区域补全是否正确。</p>
    <img src="assets/paired_p95.svg" alt="20 栋逐栋 P95 配对图；11 改善、6 持平、2 退化、1 失败"><table><thead><tr><th>建筑</th><th>基准 P95</th><th>候选 P95</th><th>判定</th></tr></thead><tbody>{table}</tbody></table>
    <h2>同视角横向比较</h2><p>每栋依次为输入点云、固定基准、上一版和候选；第一轮的上一版就是基准。点云仅为显示降采样，评测使用全部有限原始点。展示居中未写入 OBJ。七视角原图与模型哈希随冻结版本保存。</p>
    <p><a href="assets/overview.png">打开 20 栋总览</a> · <a href="data.json">逐栋原始数值</a></p>{''.join(cards)}
    <h2>线框派生数据：先限定可用范围</h2><p>52 对点云 / 线框中，第二版产生 {dataset_counts.get('derived_unvalidated',0)} 个补全候选，{dataset_counts.get('failed',0)} 个转换失败；{len(passed)} 个通过当前几何筛选。屋面来自投影闭环，墙面与底面由假设补出。坐标已恢复，逐面来源可查。</p>
    <p>训练清单仅作派生监督候选。通过检查不等于语义正确；自交筛查不覆盖共享顶点的所有交叉情况。禁止把这些候选作为独立测试 Mesh 真值。</p><p><a href="derived_qa.json">Blender 几何检查记录</a></p>
    <h2>已完成与待验证</h2><p>已完成历史三栋逐字节复现、20 栋基准与候选、外部评测、F0–F5 反馈接口、知识条目、不可覆盖版本归档和渲染校验。这一轮由当前交互会话提出修改；未进行固定模型、多种子反馈消融，未证明递归改进能力。</p>
    <p>下一步：修复凹轮廓与屋面分区装配的相容性，完善局部平面支持和高差处理；获得完整 Mesh 真值及城市分组后复现开源基线，按完整研究计划开展 E1–E10。固定评价标准，失败仍计入预算。</p>
    <footer><small>依据：冻结算法、原始点云 SHA256、逐栋外部评测、Blender 5.2.2 同相机输出。报告构建程序：scripts/buildingworld/export_research_report.py。无外部脚本或网络字体依赖。</small></footer></main></html>'''
    (out/'index.html').write_text(doc,encoding='utf-8')
    (out/'visualization-brief.md').write_text('''# 可视化设计与本地专项检查
介质：可离线 HTML + SVG/PNG + JSON。常规数据报告，不使用概念美术或动画。
1. 配对图：本地统计图专项；逐栋同输入 P95；x 为源单位、y 为建筑；圆/方形区分版本；失败显示文字，原始表格为无障碍替代。
2. 渲染小多图：本地三维专项；四列同相机、尺度、材质；缺失图保留失败状态；点击全分辨率静态图；七视角另存。
3. 残差图：本地几何专项；相同原始点、XY 范围和 0–10 色标；显示截断不影响数值；图不是完整建筑轮廓真值。
4. 总览：20 栋全部纳入，禁止只展示最好建筑。逐栋标题和数值提供图像替代信息。
QA：构建时断言渲染源模型 SHA 与评测一致；浏览器检查桌面和窄屏；不通过微小样本推断泛化或置信区间。
''',encoding='utf-8')
    return data


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--experiment',required=True);ap.add_argument('--derived',required=True);ap.add_argument('--output',required=True)
    args=ap.parse_args();build(args.experiment,args.derived,args.output)
