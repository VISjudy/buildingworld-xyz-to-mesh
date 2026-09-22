"""Publish local package verification and maintain project navigation."""
from pathlib import Path
import collections,csv,html,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from harness.io import sha256,read_obj
RUN=ROOT.parent/'submissions/2026-09-22-initial-v0.1.0-test4000'
OUT=ROOT/'reports/2026-09-22-initial-v010-test4000'


def append(path,text):
    p=ROOT/path;s=p.read_text(encoding='utf-8');assert text.strip()not in s
    p.write_text(s.rstrip()+'\n\n'+text.strip()+'\n',encoding='utf-8')


def main():
    summary=json.loads((RUN/'audit/summary.json').read_text(encoding='utf-8'))
    rows=json.loads((RUN/'audit/results.json').read_text(encoding='utf-8'))
    assert len(rows)==4000 and summary['obj_count']==4000
    # Independent loader pass over every non-empty organizer-format OBJ.
    import trimesh,numpy as np
    checked=0
    for r in rows:
        p=RUN/'obj'/f"{r['id']}.obj"
        if r['status']=='generated':
            mesh=trimesh.load(p,force='mesh',process=False)
            parsed=read_obj(p)
            assert len(mesh.vertices)==r['vertices']and len(mesh.faces)==r['triangles']
            assert np.array_equal(mesh.faces,np.asarray(parsed['faces']))
            assert np.array_equal(mesh.vertices,parsed['vertices'])
            checked+=1
        else:assert p.stat().st_size==0
    OUT.mkdir(exist_ok=False)
    for name in ['summary.json','results.json','protocol.json','inputs.json']:
        shutil.copyfile(RUN/'audit'/name,OUT/name)
    errors=dict(collections.Counter(r['error']for r in rows if r['status']!='generated'))
    proof={'trimesh_roundtrip_nonempty_checked':checked,'vertex_and_triangle_arrays_identical':True,
           'empty_placeholders_checked':4000-checked,'source_coordinate_roundtrip_max_error':max(r.get('roundtrip_max_error',0)for r in rows),
           'algorithm_sha256':sha256(RUN/'source/algorithm.py'),'raw_inputs_unchanged':True,
           'self_intersection':'not_checked','platform_acceptance':'not_tested','zip_verification':'summary.json'}
    (OUT/'verification.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    cols=['id','status','points','vertices','polygon_faces','triangles','topology_pass','watertight','winding_consistent','degenerate_triangles','seconds','obj_bytes','obj_sha256','error']
    with(OUT/'per_building.csv').open('x',encoding='utf-8-sig',newline='')as f:
        writer=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    frozen=ROOT/'releases/v0.1.0-challenge4000-submission-v001';frozen.mkdir(exist_ok=False)
    shutil.copytree(RUN/'source',frozen/'source',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (frozen/'reports').mkdir()
    for name in ['summary.json','protocol.json','inputs.json']:
        shutil.copyfile(OUT/name,frozen/'reports'/name)
    (frozen/'summary.md').write_text('''# Initial v0.1.0 challenge4000 packaging

Unchanged initial algorithm, input-only bbox diagonal30, inverse source coordinates.
Convex polygon fan triangulation and organizer process=False writer. Empty failures preserved.
Replay with `python source/run_submission.py --input ORIGINAL_LIDAR_XYZ --output NEW_ABSOLUTE_DIRECTORY --workers 6`.
The complete local OBJ/ZIP package is under `D:/codex/lidar2building/submissions/2026-09-22-initial-v0.1.0-test4000/`.
This release tracks reproducible source and audits; original point clouds/intermediates/ZIP remain local.
No platform score obtained; complete paired432/test130 remain locked.
''',encoding='utf-8')
    manifest={'version':frozen.name,'algorithm_sha256':summary['algorithm_sha256'],'package_sha256':summary['zip_sha256'],
              'files':{p.relative_to(frozen).as_posix():sha256(p)for p in frozen.rglob('*')if p.is_file()}}
    (frozen/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    failures=''.join(f'<tr><td>{html.escape(r["id"])}</td><td>{html.escape(r["error"])}</td><td>0字节同名OBJ</td></tr>'for r in rows if r['status']!='generated')
    n=summary['generated_meshes'];empty=4000-n;valid=summary['topology_pass'];bad=n-valid
    title=f'4,000 个同名 OBJ 已打包：{n:,} 个网格，{empty} 个失败空文件'
    body=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>initial v0.1.0 提交包检查</title>
<style>body{{margin:0;background:#f2f5f5;color:#20343e;font:16px/1.8 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:30px 18px}}section{{background:white;border:1px solid #d9e1e3;padding:22px;margin:18px 0;border-radius:8px}}h1{{font-size:30px;line-height:1.4}}a{{color:#006985}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #d9e1e3;padding:9px;text-align:left}}code{{overflow-wrap:anywhere}}.bar{{display:flex;height:26px;min-width:260px}}.pass{{background:#23798b}}.bad{{background:#ad741d}}.empty{{background:#ac4946}}input{{padding:10px;min-height:24px;max-width:90%}}.note{{border-left:4px solid #ad741d;padding:12px;background:#fff7e7}}[hidden]{{display:none}}@media(max-width:500px){{h1{{font-size:25px}}section{{padding:14px}}}}</style>
<main><p>2026-09-22 · initial v0.1.0 · 比赛4000输入 · 本地打包验证</p><h1>{title}</h1>
<p class="note">已完成本地文件格式与压缩包验证，尚未上传比赛平台，没有官方分数。空文件表示原算法失败，不能计作成功网格。通过拓扑检查也不等于几何重建准确。</p>
<section><h2>提交文件</h2><p><a href="{Path(summary['zip']).as_uri()}">下载可直接选择上传的ZIP</a> · <a href="{(RUN/'obj').as_uri()}">独立OBJ目录</a> · <a href="per_building.csv">逐栋状态CSV</a></p><p>ZIP根目录仅含 <code>1.obj … 4000.obj</code>，无额外文件夹、MTL、日志或说明。大小 {summary['zip_bytes']:,} 字节。下载链接指向本机文件。</p><p>SHA256：<code>{summary['zip_sha256']}</code></p></section>
<section><h2>生成情况与格式检查</h2><div class="scroll"><div class="bar" role="img" aria-label="拓扑通过{valid}，有网格但拓扑未通过{bad}，空文件{empty}"><span class="pass" style="width:{valid/40}%"></span><span class="bad" style="width:{bad/40}%"></span><span class="empty" style="width:{empty/40}%"></span></div></div><table><tr><th>类别</th><th>数量</th></tr><tr><td>有网格且当前拓扑通过</td><td>{valid}</td></tr><tr><td>有网格但当前拓扑未通过</td><td>{bad}</td></tr><tr><td>算法失败，按官网保存空文件</td><td>{empty}</td></tr><tr><td>输入与ZIP同名一一对应</td><td>4000 / 4000</td></tr></table><p>已核对全部源输入哈希、4000条压缩记录、CRC和逐文件哈希；{checked}个非空OBJ经独立trimesh重新加载，顶点和三角面数组一致。源坐标保存最大舍入误差 {proof['source_coordinate_roundtrip_max_error']:.3g}。完整自交检测未执行。</p></section>
<section><h2>算法与导出边界</h2><p>使用此前报告initial v0.1.0的冻结算法及相同输入预处理：只根据输入XYZ将包围盒对角线变为30，重建后逆变换恢复源坐标。没有引入FULL、F3或v0.5.1的修复，不使用GT。</p><p>原算法输出凸多边形，先按原面顺序扇形三角化，再调用官网推荐函数：<code>trimesh.Trimesh(vertices=vertices, faces=faces, process=False)</code>。没有自动焊接、补洞或调整立面高度。三角化改变面数统计，应在比赛结果解释中披露。</p><p>官网推荐函数在顶点或面为空时创建空文件。本轮失败均依照该约定保存，平台如何计入分数仍须实际上传确认。</p><p><a href="https://huggingface.co/spaces/BuildingWorld/10thLiDARConference">官网 Submission information → 推荐网格保存代码</a> · <a href="protocol.json">运行协议</a> · <a href="verification.json">加载检查</a> · <a href="summary.json">压缩包完整性</a></p></section>
<section><h2>失败清单</h2><p>{html.escape(str(errors))}</p><label>按建筑ID查找 <input id="q" inputmode="numeric" placeholder="如 132"></label><p id="count" aria-live="polite"></p><div class="scroll"><table><thead><tr><th>ID</th><th>失败原因</th><th>导出处理</th></tr></thead><tbody>{failures}</tbody></table></div></section>
<section><h2>目录与复现</h2><p><code>{RUN.as_posix()}</code></p><p>obj：4000个提交文件；source：冻结源码与依赖；audit：输入哈希、逐栋状态和校验；intermediate：归一化输入及原多边形输出；ZIP单独位于该目录根部。原始数据、旧版本和失败记录保持完整。</p><p>本次仅是用户明确指定比赛输入的推理与打包，完整配对训练432/封存测试130仍未启用。平台上传不在本次已完成状态内。</p></section></main>
<script>const q=document.querySelector('#q'),rows=[...document.querySelectorAll('tbody tr')];function apply(save){{let n=0;for(const r of rows){{r.hidden=!r.cells[0].textContent.includes(q.value);if(!r.hidden)n++}}document.querySelector('#count').textContent=`显示 ${{n}} / {empty} 个失败样本`;if(save){{const u=new URL(location);u.searchParams.set('q',q.value);history.replaceState(null,'',u)}}}}q.value=new URL(location).searchParams.get('q')||'';q.addEventListener('input',()=>apply(true));apply(false);addEventListener('popstate',()=>{{q.value=new URL(location).searchParams.get('q')||'';apply(false)}});</script></html>'''
    (OUT/'index.html').write_text(body,encoding='utf-8')
    (OUT/'mini-brief.md').write_text('OpenAI web data visualization: local report route. One count composition bar plus exact table; direct labels and colors are redundant. Source is immutable per-case audit; no fabricated precision score. Native HTML/CSV fallback, URL-backed failure ID filter, desktop/mobile QA. Standard established report style, no new concept design. Local statistical and accessibility pass. ZIP/OBJ links reference verified local artifacts.\n',encoding='utf-8')
    text=f'''slug: initial-v010-test4000
日期: 2026-09-22
状态: 已定案（本地推理与打包完成，未上传）
一句结论: {n}/4000成功生成网格，{empty}失败按官网规则输出空OBJ；ZIP根目录4000文件且CRC/哈希通过。
产物路径: ../submissions/2026-09-22-initial-v0.1.0-test4000/；reports/2026-09-22-initial-v010-test4000/；releases/v0.1.0-challenge4000-submission-v001/
下一步: 用户上传ZIP进行有限外部验证；不得将平台分数接入自动演化。

原算法SHA256：{summary['algorithm_sha256']}。按报告initial v0.1.0同一输入归一化（bbox对角线30）、源坐标恢复。原脚本逐字节冻结，仅路径适配。凸多边形扇形三角化后按官网推荐trimesh process=False保存，面数与原多边形版本不同，几何不补洞/修复。无GT、无算法回退。

总4000次推理（先12个检查再恢复剩余3988，不重复），所有原始输入SHA复核。当前拓扑通过{valid}，有网格但拓扑未通过{bad}。失败原因：{errors}。空文件只表达失败，不代表网格成功或平台已接受。无完整自交检查，无官方成绩。

独立trimesh重载{checked}个非空OBJ，顶点和三角面数组一致；所有4000压缩条目仅同名OBJ，无子目录，CRC及内容SHA256一致。ZIP {summary['zip_bytes']}字节，SHA256 {summary['zip_sha256']}。

代码/审计/依赖冻结进Git；4000OBJ、ZIP、归一化输入和中间多边形输出留在有序的本地submissions目录。保留失败日志和原始输入。本次用户明确授权比赛4000推理，不改变完整配对432/130阶段锁。
'''
    (Path(__file__).parent/'summary.md').write_text(text,encoding='utf-8')
    (RUN/'README.md').write_text(text,encoding='utf-8')
    append('experiments/INDEX.md',f'| initial-v010-test4000 | 本地生成与打包已定案，未上传 | {n}网格＋{empty}失败空OBJ，4000同名文件ZIP校验通过 | experiments/2026-09-22/initial-v010-test4000/summary.md；reports/2026-09-22-initial-v010-test4000 |')
    append('prompt/registers/research.md',f'''## 比赛4000 initial打包（2026-09-22）

用户明确指定 `../dataset/testDataset/LiDAR_xyz` 的1—4000，采用报告initial v0.1.0同一预处理运行，未修改算法。{n}成功网格、{empty}原算法失败空文件，{valid}通过当前拓扑；空文件按官网推荐函数输出。ZIP根目录4000同名OBJ，CRC和SHA全部核对，尚未上传，无官方分数。

入口 `experiments/2026-09-22/initial-v010-test4000/summary.md`；报告 `reports/2026-09-22-initial-v010-test4000/`；本地包 `../submissions/2026-09-22-initial-v0.1.0-test4000/`。冻结源码 `releases/v0.1.0-challenge4000-submission-v001`。新实验入口run_submission.py支持初次运行/断点恢复；导出三角化会改变面片数量统计，不能把原多边形面数直接对应比赛F_Ratio。完整配对432/130仍锁定。
''')
    append('prompt/protocols/dataset-stages.md','''## 2026-09-22 比赛4000推理授权

用户明确要求用initial v0.1.0对独立目录 `../dataset/testDataset/LiDAR_xyz` 的4000输入生成提交OBJ/ZIP。该授权仅适用于比赛4000的冻结基准推理和打包，不将完整配对训练432/封存130解锁。运行记录 `experiments/2026-09-22/initial-v010-test4000/summary.md`。不使用比赛GT，尚未上传或获得官方分数；先前development20已从该来源开发，后续成绩不能宣称对4000全部零开发接触。
''')
    append('prompt/knowledge/experience-index.md','| EXP-S007 | 工程验证 | 官方导出允许空OBJ表达失败；ZIP文件齐全与成功网格数必须分别报告 | reports/2026-09-22-initial-v010-test4000/summary.json |')
    with(ROOT/'prompt/knowledge/experiences.jsonl').open('a',encoding='utf-8')as f:
        f.write(json.dumps({'id':'EXP-S007','date':'2026-09-22','kind':'submission_format','status':'validated_engineering',
             'claim':'官方推荐保存函数对空顶点/面创建空OBJ；批量提交必须分开报告占位数和成功网格数。',
             'conditions':['2026-09-22官网Submission information；initial v0.1.0比赛4000'],
             'evidence':['reports/2026-09-22-initial-v010-test4000/summary.json'],
             'counterexamples':['ZIP本地格式通过不代表平台已接受或重建精度高。'],
             'next_action':'有限官方验证，保留失败并区分三角面与原多边形面统计。'},ensure_ascii=False)+'\n')
    p=ROOT/'memory.md';s=p.read_text(encoding='utf-8');s=s.replace('## 快速恢复（顺序）',f'- 2026-09-22 按用户授权对比赛4000输入运行initial v0.1.0：{n}个网格＋{empty}个失败空OBJ，已打包并校验，未上传。包在 `../submissions/2026-09-22-initial-v0.1.0-test4000/`，报告 `reports/2026-09-22-initial-v010-test4000/`；完整配对432/130仍锁定。\n\n## 快速恢复（顺序）');p.write_text(s,encoding='utf-8')
    for file,row,anchor in [
      ('AGENTS.md','| Competition submission | 提交, 打包, ZIP, 4000 | experiments/2026-09-22/initial-v010-test4000/summary.md |','| Experience |'),
      ('prompt/INDEX.md','| 比赛提交包 | 提交、打包、ZIP、4000 | ../experiments/2026-09-22/initial-v010-test4000/summary.md |','| 经验检索 |')]:
        p=ROOT/file;s=p.read_text(encoding='utf-8');assert row not in s;s=s.replace(anchor,row+'\n'+anchor);p.write_text(s,encoding='utf-8')
    append('.gitattributes','releases/v0.1.0-challenge4000-submission-v001/** -text\nreports/2026-09-22-initial-v010-test4000/** -text')
    print(json.dumps({'report':str(OUT),'loader_verified':checked,'empty':empty,'release':str(frozen)},ensure_ascii=False))


if __name__=='__main__':main()
