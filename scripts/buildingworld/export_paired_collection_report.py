"""Small offline report for the real/synthetic collection, preserving source strata."""
import argparse
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.io import read_json, write_json
from harness.workflow import run_batch


def report(dataset, output):
    dataset, out = Path(dataset).resolve(), Path(output).resolve()
    s = read_json(dataset / 'summary.json')
    spec = read_json(dataset / 'manifest.json')
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(dataset / 'summary.json', out / 'summary.json')
    write_json(out / 'inventory.json', {'scope': s['scope'], 'samples': [
        {k: r[k] for k in ['id', 'source_id', 'dataset', 'source_type', 'evaluation_stratum',
                           'author_split', 'project_split', 'starter_overlap',
                           'point_sha256', 'mesh_sha256']} for r in spec['samples']]})
    blocked = []
    for name in ['all_train', 'all_test', 'real_zurich_train', 'real_zurich_test',
                 'synthetic_mini_train', 'synthetic_mini_test']:
        try:
            run_batch('source-does-not-exist.py', dataset / ('manifests/' + name + '.json'),
                      out / ('must-not-run-' + name))
        except ValueError as exc:
            blocked.append({'manifest': name, 'message': str(exc)})
        else:
            raise ValueError('Stage gate failed')
    write_json(out / 'stage-verification.json', {'blocked_manifests': blocked,
                                               'reconstruction_executed': False})
    real, sim = s['sources']['real_zurich'], s['sources']['synthetic_mini']
    columns = [(real, 'Zurich 真实机载 LiDAR', '363 / 28,415 原始对', '作者源坐标已共同还原'),
               (sim, 'PolyGNN mini 仿真 ALS', '199 / 200 原始对', '作者归一化坐标，不能标米')]
    rows = ''.join(f'''<tr><th scope="row">{label}</th><td>{r['qualified_pairs']}</td>
<td>{r['project_splits']['train']}</td><td>{r['project_splits']['test']}</td></tr>''' for r, label, _, _ in columns)
    totals = s['project_splits']
    html = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>真实与仿真完整本地集合 · 562 对</title><style>
body{{font-family:system-ui,"Microsoft YaHei",sans-serif;background:#f5f7f8;color:#19333b;line-height:1.75;margin:0}}
main{{max-width:980px;margin:auto;padding:40px 24px 70px}}h1{{font-size:clamp(26px,4vw,42px);line-height:1.3}}h2{{font-size:22px;margin-top:34px}}
header{{border-bottom:3px solid #09696b;padding-bottom:20px}}.eyebrow{{font-weight:700;color:#09696b}}.lead{{font-size:19px}}
table{{border-collapse:collapse;width:100%;table-layout:fixed;background:#fff}}th,td{{padding:14px 12px;border-bottom:1px solid #d6e0e2;text-align:right;vertical-align:top}}th:first-child{{width:43%;text-align:left}}thead,tfoot{{background:#e6eff0}}td{{font-variant-numeric:tabular-nums;font-weight:650}}
aside{{background:#e8eef0;border-left:4px solid #506b77;padding:15px 20px;margin:22px 0}}li{{margin:9px 0}}code{{overflow-wrap:anywhere;font-size:.88em}}a{{color:#056277;text-underline-offset:3px}}summary{{padding:12px 0;cursor:pointer;font-weight:650}}summary:focus-visible,a:focus-visible{{outline:3px solid #aa6500}}footer{{font-size:14px;border-top:1px solid #bbcdd2;padding-top:20px;margin-top:30px}}
@media(max-width:600px){{main{{padding:24px 16px 45px}}th,td{{padding:10px 6px;font-size:14px}}th:first-child{{width:38%}}.lead{{font-size:17px}}}}@media print{{body{{background:white}}main{{padding:0}}}}
</style><main><header><div class="eyebrow">2026-09-21 · 数据准备 · 完整集尚未运行重建</div>
<h1>真实 363 对 + 仿真 199 对，<br>统一纳入完整本地集合</h1>
<p class="lead">按用户确认，本轮包括 Zurich 真实采集数据与已下载 PolyGNN mini 的全部合格数据。完整集合共 <strong>{s['total_quality_pairs']} 对</strong>，分别保存来源和评测分组。</p></header>
<h2>训练与封存测试按来源分开</h2><table><caption>数量可相加；不同坐标单位的几何误差不能直接混合汇总</caption>
<thead><tr><th>数据来源</th><th>合格</th><th>训练</th><th>测试</th></tr></thead><tbody>{rows}</tbody>
<tfoot><tr><th>本地集合合计</th><td>{s['total_quality_pairs']}</td><td>{totals['train']}</td><td>{totals['test']}</td></tr></tfoot></table>
<p>固定 78 对入门样例已包含在训练部分：38 对真实 + 40 对仿真。封存测试与入门样例重叠为 0；78 不是额外增加的数据量。</p>
<aside><strong>当前仍只允许用 78 对迭代。</strong>新增训练样本和全部封存测试保持阶段锁。待入门算法稳定、完成验收并冻结代码/评测器/配置后，再进入完整集阶段。本次只做数据 QA，没有提前运行重建或获取测试分数。</aside>
<h2>本次新增了什么</h2><ul>
<li>仿真 mini 的 200 对已经全部审核，199 对满足既定立面回波、闭合和点云—参考 Mesh 配对门槛；全部 199 对又通过 Blender 的独立拓扑、体积和非相邻三角形相交候选检查。</li>
<li>全部合格仿真数据已导出 XYZ、gt.obj、派生 wireframe.obj 和 provenance.json；没有补造点或面。{s['synthetic_raw_files_verified']} 个原始解压文件已复核大小与 SHA256。</li>
<li>199 对全部纳入，不再限制每组 20 对；未通过的 1 对继续保留原始文件和审核记录。</li>
<li>统一索引指向真实/仿真各自的数据目录，避免重复复制；9 份清单覆盖来源、作者标签、项目划分和固定入门入口。</li></ul>
<h2>划分与解释边界</h2><ul>
<li>真实组：作者标签保留为 train 345 / test 18。18 对作者 test 已在入门集，项目封存 51 对来自作者 train；不能对作者预训练权重宣称未见。</li>
<li>仿真组：作者标签保留为 train 100 / test 99。其中 20 对作者 test 已用于入门，移入项目开发/训练用途；余下 79 对封存。项目训练为 120 对。精确哈希和当前近似形状检查没有发现跨训练/测试重叠。</li>
<li>仿真 mini 没有完整源坐标变换，本次不宣称仿真空间隔离，也不能把归一化距离标为米。真实与仿真的重建指标必须分别报告。</li>
<li>所有“合格”结论限定于已执行的几何 QA；相交候选筛查与形状相似度不能替代完整自交证明和人工语义审核。</li></ul>
<details><summary>本轮“完整”指什么</summary><p>指当前已下载 Zurich 数据与 PolyGNN mini 中所有符合门槛的数据。<a href="https://github.com/chenzhaiyu/polygnn">作者说明</a>明确区分 200 对 mini 与 Munich 完整发布库。本轮用户选择仅纳入已下载 mini 的全部合格数据，未下载后者，也没有将 mini 称为完整发布版。</p></details>
<h2>统一入口</h2><p><code>dataset/processed/complete_pairs_v001/README.md</code><br>
<code>manifests/starter78_development.json</code>：当前开发入口。<br>
<code>manifests/real_zurich_*.json</code>、<code>synthetic_mini_*.json</code>：分来源训练/测试。<br>
<code>manifests/all_*.json</code>：统一编排清单；仍带阶段锁。</p>
<p><a href="summary.json">数据摘要</a> · <a href="inventory.json">562 对划分与哈希</a> · <a href="stage-verification.json">执行门禁核验</a> · <a href="../2026-09-21-point2building-complete/index.html">真实组前阶段报告</a></p>
<footer>基于本地审核与冻结清单，使用 OpenAI data visualization 技能生成。源：Point2Building Zurich、PolyGNN mini。Git 保存代码/报告/摘要，数据只保存在本地。</footer></main></html>'''
    (out / 'index.html').write_text(html, encoding='utf-8')
    (out / 'visualization-mini-brief.md').write_text('''# Visualization mini-brief

OpenAI data visualization：reports-pdfs-and-slide-automation + strategy/critique + statistical honesty，本地复核。
任务：比较两种来源的合格、训练、测试数量，明确使用阶段；媒介：独立离线 HTML。
唯一核心视觉：语义表格，行=真实/仿真，列=合格/训练/测试；合计只加计数，禁止跨单位混合误差。每个数据点都有文字，不靠颜色编码。
前后段落说明 78 对为子集、作者与项目 test 的差异、mini 范围。原生 details 折叠背景；无 JS、网络依赖或需持久化状态。
DOM 渲染，手机保持阅读顺序，打印可用；表格行列标题与键盘 details 可访问。验收：桌面/手机无水平溢出、截图人工检查、计数守恒、门禁生效、无远程加载。
''', encoding='utf-8')
    print(out / 'index.html')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', required=True)
    p.add_argument('--output', required=True)
    report(**vars(p.parse_args()))
