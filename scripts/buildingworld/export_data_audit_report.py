"""Offline evidence report for facade-pair acquisition; raw datasets remain local."""
import argparse
from collections import Counter
import html
from pathlib import Path
import shutil
import sys
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from harness.io import read_json,write_json,sha256


def build(dataset_root,experiment,output):
    data=Path(dataset_root);exp=Path(experiment);out=Path(output);out.mkdir(parents=True,exist_ok=False)
    assets=out/'assets';assets.mkdir()
    real=read_json(data/'external/point2building/audits/facade-closed-v002/audit.json')
    initial=read_json(data/'external/point2building/audits/facade-v001/audit.json')
    screen=read_json(data/'external/point2building/audits/topology-all-v001.json')
    synthetic=read_json(data/'external/polygnn_mini/audits/facade-v001/audit.json')
    starter=read_json(data/'processed/facade_pairs_v001/manifest.json')
    groups=Counter((r['dataset'],r['author_split']) for r in starter['samples'])
    request=read_json(exp/'render_request.json');renders=read_json(exp/'renders/render_manifest.json')
    hashes={r['id']:r['source_hashes']['current'] for r in renders['samples']}
    cards=[];font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    for s in request['samples']:
        row=s['source'];assert hashes[s['id']]==row['mesh_sha256']==sha256(s['models']['current'])
        name=s['id'];canvas=Image.new('RGB',(1440,470),'#eff3f5');draw=ImageDraw.Draw(canvas)
        for i,(key,label) in enumerate([('input','Actual input returns'),('current','Author reference mesh'),('overlay','Input + reference overlay')]):
            image=Image.open(exp/'renders'/f'{name}_oblique_{key}.png').convert('RGB');canvas.paste(image,(480*i,45))
            draw.text((480*i+14,12),label,fill='#173543',font=font)
        canvas.save(assets/(name+'.png'))
        kind='真实 ALS' if row['dataset']=='point2building' else '仿真 ALS'
        # Also expose side views where facade coverage is easiest to inspect.
        for key in ['input','current','overlay']:
            shutil.copyfile(exp/'renders'/f'{name}_front_{key}.png',assets/f'{name}_front_{key}.png')
        cards.append(f'''<article><h3>{kind} · {html.escape(row['id'])}</h3><p>原作者 {row['author_split']}；几何判定的立面回波 {row['facade_points']} 点，占 {100*row['facade_fraction']:.2f}%。</p>
        <a href="assets/{name}.png"><img src="assets/{name}.png" alt="{kind} 的输入点云、作者参考 Mesh 和同相机叠加"></a>
        <details><summary>查看侧视立面</summary><div class="side">{''.join(f'<img loading="lazy" src="assets/{name}_front_{k}.png" alt="侧视 {k}">' for k in ['input','current','overlay'])}</div></details></article>''')
    facts={'real':{'source':'Point2Building / Zurich','pairs':real['catalog_pair_count'],'train':25724,'test':2691,
        'all_mesh_topology_pass':screen['closed_count'],'initial_audit':initial['audited_count'],
        'initial_facade_pass':sum(r.get('facade_observation_pass',False) for r in initial['results']),
        'closed_stratum_audit':real['audited_count'],'closed_and_facade_pass':real['selected_count'],
        'selected_by_author_split':dict(Counter(r['split'] for r in real['results'] if r.get('selected_for_facade_development')))},
        'synthetic':{'source':'PolyGNN mini / Munich','pairs':synthetic['catalog_pair_count'],'train':100,'test':100,
        'audited':synthetic['audited_count'],'selected':synthetic['selected_count']},
        'starter':{'pairs':len(starter['samples']),'groups':{':'.join(k):v for k,v in groups.items()}},
        'thresholds':real['thresholds'],'reconstruction_experiment':False,'license_note':'See upstream data terms; raw data not redistributed in Git.'}
    write_json(out/'dataset-audit-summary.json',facts)
    for kind,source in [('point2building',real),('polygnn_mini',synthetic)]:
        slim={k:v for k,v in source.items() if k not in ['results','topology_prescreen']}
        slim['results']=[{k:v for k,v in r.items() if k not in ['points','mesh']} for r in source['results']]
        write_json(out/(kind+'-audit.json'),slim)
        archive=data/'external'/kind/'raw/archives'/('point2building_resources.tar.gz.provenance.json' if kind=='point2building' else 'mini.tar.gz.provenance.json')
        shutil.copyfile(archive,out/(kind+'-download.json'))
    shutil.copyfile(exp/'visualization-brief.json',out/'visualization-brief.json')
    doc=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>立面数据获取与审计</title>
    <style>*{{box-sizing:border-box}}body{{margin:0;background:#f4f7f8;color:#18313e;font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:1140px;margin:auto;padding:32px 24px}}h1{{font-size:34px;line-height:1.3}}h2{{margin-top:40px}}h3{{overflow-wrap:anywhere}}a{{color:#006d84}}img{{max-width:100%;height:auto}}.note{{border-left:4px solid #c57c25;padding:18px;background:#fff4df}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{padding:12px 8px;text-align:left;border-bottom:1px solid #dce3e7}}article{{background:white;border:1px solid #dce3e7;padding:20px;margin:24px 0;border-radius:8px}}.side{{display:grid;grid-template-columns:repeat(3,1fr)}}summary{{cursor:pointer}}summary:focus,a:focus{{outline:3px solid #cf7e22}}@media(max-width:600px){{main{{padding:18px 12px}}h1{{font-size:27px}}article{{padding:12px}}table{{font-size:13px}}.side{{grid-template-columns:1fr}}}}</style>
    <main><small>2026-09-21 · 数据入库审计 · OpenAI data visualization 技能工作流</small><h1>已取得真实与仿真立面点云，<br>以配对和质量检查决定用途</h1>
    <p>demo_dataset 为屋顶数据，补墙得到的 Mesh 不再承担完整建筑真值。新数据来自作者公开资源，保留原始归档、配对、坐标变换与 SHA256。</p>
    <table><thead><tr><th>来源</th><th>扫描类型</th><th>完整下载配对数</th><th>入门样例</th></tr></thead><tbody><tr><td>Point2Building · Zurich</td><td>真实机载 ALS</td><td>{real['catalog_pair_count']:,}</td><td>38（train 20 / test 18）</td></tr><tr><td>PolyGNN mini · Munich</td><td>仿真机载 ALS</td><td>{synthetic['catalog_pair_count']}</td><td>40（train 20 / test 20）</td></tr></tbody></table>
    <p class="note">入门目录共 {len(starter['samples'])} 对，是质量筛选后的开发/审核样例，不代表无偏测试集。下载包中原作者 trainset/testset 保留。真实与仿真结果必须分开，不能合并成一项真实扫描成绩。</p>
    <h2>Mesh 有墙面，还要确认点云有墙面回波</h2><p>Point2Building 全部 28,415 个 Mesh 中，{screen['closed_count']:,} 个通过当前严格三角面闭合/朝向筛查。初次按哈希顺序抽查 120 对，有 93 对满足立面观测条件；随后仅在闭合 Mesh 子集中审计 {real['audited_count']} 对，{real['selected_count']} 对通过联合筛选（train 53 / test 18）。两个抽查分母不同，不能比较通过率来宣称质量提升。</p>
    <p>PolyGNN mini 全部 200 对均审计，{synthetic['selected_count']} 对通过联合筛选；另 1 对立面支持不足，保留失败记录。大部分 Point2Building 原参考模型有屋顶、墙面和底面，但存在连接/闭合问题；原文件未修补，不能都称完美实体真值。</p>
    <h2>如何判定立面证据</h2><p>参考三角面法向距水平不超过 10°、从接近底高处跨越至少 25% 建筑高度，作为主墙面候选。输入点须距参考面不超过包围盒对角线的 0.5%，并处在墙面垂向中间 80%，以排除屋檐和底边的偶合点。至少 10 点、占比至少 0.5%、垂向跨度至少 15%。另要求点面 P95 ≤ 对角线 5%，并检查 Mesh 闭合、朝向、退化、底面。</p>
    <p>这是保守的几何证据筛选，不是逐点人工语义标注。自交尚未完整检查，ALS 四周立面覆盖也不可能由该条件保证。误差按作者坐标度量；PolyGNN mini 为归一化数据，不能直接称“米”。</p>
    <h2>实际输入与作者 Mesh</h2><p>下面 3 个真实样例和 2 个仿真样例，按入门集合的立面点比例分位选择，仅用于审查。所有图片使用每栋固定相机、尺度和材质；Mesh 为作者参考，不是本项目算法输出。</p>{''.join(cards)}
    <h2>可复现下载与坐标恢复</h2><p>Point2Building 原包 1,612,680,162 字节；PolyGNN mini 原包 163,238,451 字节。提取仅允许数据文件，不执行包内训练代码、Shell 或反序列化 checkpoint。Point2Building 按作者 <code>world = normalized × scale + center</code> 同时还原点云和 Mesh，并做重新读取检查；PolyGNN 保留其归一化坐标。</p>
    <p>作者 Point2Building 的训练加载代码会利用参考 Mesh 高程添加人工底面点。本项目下载/审核直接读取原始 XYZ，没有使用这种额外点。后续公平复现必须单列该预处理，不能把它当传感器实测回波。</p>
    <h2>后续使用</h2><p>优先用真实入门样例开发立面、屋面和地面分离诊断；仿真集合辅助验证已知几何。完整性能评测需回到作者完整测试集并声明预处理，完成近重复和空间组审计。此次完成的是数据获取与 QA，尚未运行新的重建算法训练或性能比较。</p>
    <p><a href="dataset-audit-summary.json">审计摘要</a> · <a href="point2building-audit.json">真实样例审核记录</a> · <a href="polygnn_mini-audit.json">仿真样例审核记录</a></p>
    <p>一手来源：<a href="https://github.com/prs-eth/point2building">Point2Building 作者仓库</a>、<a href="https://doi.org/10.1016/j.isprsjprs.2024.07.012">Point2Building 论文</a>、<a href="https://github.com/chenzhaiyu/polygnn">PolyGNN 作者仓库</a>、<a href="https://zenodo.org/records/14254264">PolyGNN 数据说明</a>。原始数据不随本仓库再分发，使用须遵守原来源许可。</p></main></html>'''
    (out/'index.html').write_text(doc,encoding='utf-8')
    return facts


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset-root',required=True);p.add_argument('--experiment',required=True);p.add_argument('--output',required=True)
    print(build(**vars(p.parse_args())))
