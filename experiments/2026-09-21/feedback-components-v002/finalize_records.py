"""Finalize current experiment documents without changing frozen algorithms/models."""
from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parents[3]
E=R/'experiments/2026-09-21/feedback-components-v002'
O=R/'reports/2026-09-21-feedback-components-v002'
W=R/'work/experiments/2026-09-21/feedback-components-v002'
def append(path,text):
    p=R/path;s=p.read_text(encoding='utf-8')
    assert text.strip() not in s
    p.write_text(s.rstrip()+'\n\n'+text.strip()+'\n',encoding='utf-8')
def replace(path,old,new):
    p=R/path;s=p.read_text(encoding='utf-8');assert old in s
    p.write_text(s.replace(old,new),encoding='utf-8')

# Remove links for failed outputs, retain their rows and failure messages.
p=O/'index.html';s=p.read_text(encoding='utf-8')
for row in json.loads((O/'v051_results.json').read_text(encoding='utf-8'))['samples']:
    if row['status']!='evaluated':
        bid=row['id'];old=f'<a href="../../releases/v0.5.1-starter78-comparison-v002/models/{bid}/model_source.obj">v0.5.1源坐标OBJ（失败样例无文件）</a>'
        assert old in s;s=s.replace(old,'<span>v0.5.1重建失败：没有OBJ，详见本栋指标及失败记录</span>')
p.write_text(s,encoding='utf-8')
builder=E/'build_report.py';s=builder.read_text(encoding='utf-8')
anchor="        cards.append(f'''<article"
new="        historical_link=(f'<a href=\"../../releases/{VERSIONS[\"v051\"]}/models/{bid}/model_source.obj\">v0.5.1源坐标OBJ</a>' if indexed['v051'][bid]['status']=='evaluated' else '<span>v0.5.1重建失败：没有OBJ，详见本栋指标及失败记录</span>')\n"+anchor
assert anchor in s;s=s.replace(anchor,new)
s=s.replace('<a href="../../releases/{VERSIONS[\'v051\']}/models/{bid}/model_source.obj">v0.5.1源坐标OBJ（失败样例无文件）</a>','{historical_link}')
builder.write_text(s,encoding='utf-8')

replay=json.loads((W/'frozen-replay-check-r2/results.json').read_text(encoding='utf-8'))['samples'][0]
assert replay['status']=='evaluated'
bid=replay['id'];raw=json.loads((O/'FULL_results.json').read_text(encoding='utf-8'))['samples']
old=next(r for r in raw if r['id']==bid)
assert old['mesh_sha256']==replay['mesh_sha256']
assert all(old[k]==replay[k] for k in ['CD','ECD','NC','p95','topology_pass'])
(O/'frozen-replay-verification.json').write_text(json.dumps({'id':bid,'OBJ_byte_identical':True,'CD_ECD_NC_P95_topology_identical':True,'source':'releases/v0.1.3-full-feedback-v002/source/reproduce.py','initial_invocation_note':'An initial invocation used a nonmatching ID and stopped before inference; corrected using the input manifest.'},indent=2),encoding='utf-8')

summary='''slug: feedback-components-v002
日期: 2026-09-21
状态: 已定案（单候选探索实验；机制研究继续）
一句结论: 综合反馈候选78/78通过当前拓扑检查；加入图像的候选几何优于文本知识候选，但未证明因果贡献；高度检查本批零收益。
产物路径: reports/2026-09-21-feedback-components-v002/；work/experiments/2026-09-21/feedback-components-v002/；releases/v0.1.3-*-v002/；releases/v0.5.1-starter78-comparison-v002/
下一步: 保持78开发范围，做多次独立提议和反馈逐层去除；优先解决真实组缺少可信底高、多高度屋面和逐栋回归。完整训练432/封存130保持锁定。

## 执行与归因

3个隔离模型提议，同一v0.1.0初始代码、同一discovery24文本反馈；每个最多140修改行、10次工具调用和1次语法检查。T无显式知识、TK知识v002、FULL与TK同知识并实际查看2张图。精确模型服务快照/Token不可观测，不宣称严格等成本。没有把后续78栋结果返回给提议模型。

初版知识K01–K08仍保留；旧F0/F3知识相同，旧策略演化只改4条经验与排序，旧图片仅事后展示。本轮K09区分标高与离地高度，另加X01/X02经验；六层文本增加定位和支持/底高证据。详见 docs/FEEDBACK_COMPONENTS_V002.md。尚未完成六层逐项消融、深度/法向图、完整自交或新的递归迁移证明。

| 条件 | 有评测输出 | 当前拓扑通过 |
|---|---:|---:|
| 旧初始/F0（复用） | 71/78 | 71/78 |
| 旧F3（复用） | 77/78 | 77/78 |
| T原始提议 | 0/78 | 0/78 |
| T等价兼容修复 | 77/78 | 76/78 |
| TK等价兼容修复 | 78/78 | 78/78 |
| FULL | 78/78 | 78/78 |
| FULL关闭高度检查 | 78/78 | 78/78 |
| 历史v0.5.1 | 76/78 | 28/78 |

6次78栋批量=468次新尝试；复用旧234次结果；另有历史脚本包装一致性、FULL整体Z平移及冻结重放各1次检查。初次冻结重放命令ID未匹配，没有进行推理，保留其空目录。raw T NumPy2.5.3二维cross失败全部保留，T/TK分别作1/2处代数等价API修复；raw TK未跑，不能将修复收益归因于知识。

FULL相对TK共同成功样本：真实38栋平均ΔCD=-0.033374、ΔECD=-0.074108；仿真40栋ΔCD=-0.080656、ΔECD=-0.217885。都是分析坐标单位，非米/官方分数。一组一个多算子提议，图片与文本信息不严格等量，只支持候选差异。T→TK增加覆盖与有效性但共同成功几何退化，不能报告知识必然有益。FULL与F0、v0.5.1仍存在指标取舍，逐栋结果全部保留。

关闭高度检查后78份OBJ与FULL逐字节相同，贡献为0。真实最低回波与参考底高误差中位数37.75%GT高度，37/38最低回波高于底高超过2%；仿真中位数1.51%。屋顶q99与GT最高点差中位数真实2.95%/仿真1.35%，只支持端点高度信息。绝对Z阈值无坐标不变性；默认最低回波底面依然是假设。FULL仅重选高于临时底面的有支持平面，否则失败，未实现异常Z恢复真实底高。

## 验证与交付

387个成功新输出通过源坐标往返和渲染模型哈希一致性检查；六个版本冻结源码、依赖、知识、反馈、模型和七视角。历史v0.5.1使用归档原字节，直接脚本与包装OBJ相同。FULL单栋整体Z+500输出等量移动；冻结重放一栋OBJ及指标完全相同。浏览器、Git快照校验和测试证据见报告目录，QA评价不作为研究证据。

统一相机横向：输入｜初始｜F0｜F3｜FULL｜v0.5.1｜GT；另有T/TK/FULL消融排列及叠加，可按ID和七视角筛选、记录人工评价并导出。所有78对都是开发样本，当前拓扑检查不包含完整自交，78/78不代表高准确率或泛化成功。
'''
(E/'summary.md').write_text(summary,encoding='utf-8')
append('experiments/INDEX.md','| feedback-components-v002 | 单候选探索已定案 | 综合反馈78/78当前拓扑通过；图像候选改善但因果未证实，高度检查零收益；v0.5.1纳入同样本比较 | experiments/2026-09-21/feedback-components-v002/summary.md；reports/2026-09-21-feedback-components-v002 |')
append('prompt/registers/research.md','''## 最新：反馈组成、图像与高度（v002）

入口 `experiments/2026-09-21/feedback-components-v002/summary.md`；报告 `reports/2026-09-21-feedback-components-v002/index.html`；方法 `docs/FEEDBACK_COMPONENTS_V002.md`。3个隔离提议T/TK/FULL，6组批量468次新尝试（含保留的原T API失败与历史v0.5.1）；完整集未启用。

FULL与TK均78/78当前拓扑通过；T兼容版77输出/76通过；原归档v0.5.1为76输出/28通过。FULL相对TK两来源共同成功CD/ECD均值降低，单候选/多算子与不等信息量不能证明图像因果。高度检查开关78份OBJ完全一致。FULL未在所有指标上优于F0或历史版。

旧知识K01–K08不改；新 `config/knowledge/rules-v002.json` 增K09和X01/X02，仅供新实验使用。六层反馈增强，FULL确实查看2张诊断图；旧图片没有进入模型反馈。尚未完成逐层去除和新迁移验证。v002报告、六冻结包、模型来源、兼容修正和七视角均独立保留。下一步多次独立提议及真实底高/多屋面问题，不能依据拓扑通过升级完整集。
''')
append('prompt/registers/datasets.md','''## Z与立面高度审核（starter78，2026-09-21）

证据 `reports/2026-09-21-feedback-components-v002/height-audit/` 与 `docs/FEEDBACK_COMPONENTS_V002.md`。真实38对最低回波相对参考底高误差中位数37.75%建筑高度，37/38高于底高超过2%；仿真40对中位数1.51%。屋顶q99相对GT最高点误差中位数真实2.95%、仿真1.35%，不能推断完整屋顶曲面或真实地面。参考Mesh底高也不保证为可见地形。

canonical零点为输入包围盒中心，不是地面；真实可恢复作者源坐标但CRS/垂直基准未独立核准，mini为作者归一化坐标。建筑高度应为可信屋顶标高减可信底高；不能按绝对Z阈值跨数据源截断。2%/5%是描述误差带而非部署门槛。没有对432训练/130封存进行重建或本轮高度审核。
''')
entry='| 反馈组成与高度 | 消融、图像、综合反馈、v0.5.1、Z值、高度 | ../docs/FEEDBACK_COMPONENTS_V002.md；../experiments/2026-09-21/feedback-components-v002/summary.md |'
replace('prompt/INDEX.md','| 经验检索 |',entry+'\n| 经验检索 |')
replace('AGENTS.md','| Experience |','| Feedback components | 消融, 图像, 综合反馈, v0.5.1, Z值, 高度 | docs/FEEDBACK_COMPONENTS_V002.md; experiments/2026-09-21/feedback-components-v002/summary.md |\n| Experience |')
replace('memory.md','最新实验报告 `reports/2026-09-21-starter78-feedback-pilot/`','最新实验报告 `reports/2026-09-21-feedback-components-v002/`')
replace('memory.md','## 快速恢复（顺序）','''- v002综合反馈/文本知识均78/78当前拓扑通过，历史v0.5.1为76输出/28通过；单候选图像差异未证明因果，高度检查开关全部OBJ相同。新知识v002增K09与2条经验；旧8条规则不改。真实37/38最低回波不足以代表底高，禁止绝对Z推断立面。方法与版本解释见 `docs/FEEDBACK_COMPONENTS_V002.md`；完整集保持锁定。

## 快速恢复（顺序）''')
replace('README.md','**最新小试：**','**前一轮小试：**')
replace('README.md','**前一轮小试：**','''**最新反馈组成实验：** [v002可视化报告](reports/2026-09-21-feedback-components-v002/index.html)明确知识库、每版算法改动及图像/高度检查贡献，并增加归档v0.5.1。综合候选78/78通过当前拓扑检查；历史版76输出/28通过。图像条件得到更低的配对CD/ECD，但单候选不证明因果；高度检查本批零收益。保留6个新冻结目录、逐栋七视角和全部失败，完整集仍锁定。见[方法与限制](docs/FEEDBACK_COMPONENTS_V002.md)、[实验记录](experiments/2026-09-21/feedback-components-v002/summary.md)。

**前一轮小试：**''')
append('.gitattributes','''releases/v0.1.3-*-v002/** -text
releases/v0.5.1-starter78-comparison-v002/** -text
reports/2026-09-21-feedback-components-v002/** -text''')
records=[
 ('EXP-H002','hypothesis','图像条件的候选较文本知识候选共同成功CD/ECD均值降低，但单提议多算子不足以证明图像因果。','相同初始代码、discovery24文本与知识，FULL实际看2图；精确Token不明。','FULL与F0/v0.5.1仍有指标取舍，知识组相对无显式知识几何有退化。','多次独立提议，同等信息与成本控制。'),
 ('EXP-L003','limitation','真实屋顶Z有信息，但最低回波不能确定建筑底高；禁止绝对Z阈值推断立面高度。','starter78真实38/仿真40，参考Mesh最低面作为比较对象。','真实37/38最低回波高于参考底面超2%；mini可有低端噪声。','引入可信地面/地形证据或明确底高不确定性。'),
 ('EXP-F003','validated_engineering','FULL关闭相对临时底面角点检查后78份OBJ相同，本批可测贡献为0。','同一代码仅关闭一个检查，固定评测/输入。','零激活不证明异常输入下规则无效，也不能宣称恢复真实底高。','独立异常输入压力测试，保持固定验收。'),
 ('EXP-C003','correction','NumPy2.5.3二维cross兼容异常导致原T全部失败，等价修复必须与反馈收益分开。','原候选及失败保留；T一处、TK两处代数等价修复，rawTK未评测。','兼容修复后的可运行性不能归因为知识或图像。','后续固定依赖/API约定并预留相同兼容检查预算。')]
p=R/'prompt/knowledge/experiences.jsonl'
with p.open('a',encoding='utf-8') as f:
 for id,status,claim,conditions,counter,next_action in records:
  f.write(json.dumps({'id':id,'date':'2026-09-21','kind':'feedback_components','status':status,'claim':claim,'conditions':[conditions],'evidence':['experiments/2026-09-21/feedback-components-v002/summary.md','reports/2026-09-21-feedback-components-v002/summary.json'],'counterexamples':[counter],'next_action':next_action},ensure_ascii=False)+'\n')
append('prompt/knowledge/experience-index.md','''## 反馈组成v002新增记录

| ID | 状态 | 结论 |
|---|---|---|
| EXP-H002 | 假设 | 图像候选配对几何改善，因果未证实 |
| EXP-L003 | 限制 | 标高不等于立面高度，底高通常未观测 |
| EXP-F003 | 工程事实 | 本批高度检查开关零收益 |
| EXP-C003 | 纠正 | API兼容修复与知识/反馈贡献分开 |

证据统一见 `experiments/2026-09-21/feedback-components-v002/summary.md`。新规则 `config/knowledge/rules-v002.json` 仅用于v002，旧版本不变。
''')
print('Records finalized; frozen replay identical.')
