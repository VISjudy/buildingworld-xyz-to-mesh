"""Static evidence views and a local, dependency-free review catalogue."""
from pathlib import Path
import sys,os,json,html,csv
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parents[1]/'work/runtime/deps'));os.environ['MPLCONFIGDIR']=str(HERE.parents[1]/'work/runtime/mplconfig')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection,Line3DCollection
OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'work/experiments/train20_review'
batch=json.loads((OUT/'batch_results.json').read_text(encoding='utf8'))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titleweight':'bold'})

def structural_edges(m):
    v=np.array(m['vertices']);adj={};norm=[]
    for i,f in enumerate(m['faces']):
        p=v[f];n=np.cross(p,np.roll(p,-1,axis=0)).sum(0);norm.append(n/max(np.linalg.norm(n),1e-12))
        for a,b in zip(f,f[1:]+f[:1]):adj.setdefault(tuple(sorted((a,b))),[]).append(i)
    return np.array([v[list(e)] for e,fs in adj.items() if len(fs)!=2 or abs(np.dot(norm[fs[0]],norm[fs[1]]))<np.cos(np.deg2rad(8))])

def point_subset(p,limit=6500):
    return p[np.random.default_rng(207).choice(len(p),min(limit,len(p)),replace=False)]

def render3d(ax,p,m,kind):
    cloud=point_subset(p);v=np.array(m['vertices']) if m else p
    if m and kind!='points':
        colors=[('#bf713d' if 'roof' in s else '#a9bac5') for s in m['semantics']]
        ax.add_collection3d(Poly3DCollection([v[f] for f in m['faces']],facecolors=colors,alpha=.36 if kind=='overlay' else .97,linewidths=0))
        edge=structural_edges(m)
        if len(edge):ax.add_collection3d(Line3DCollection(edge,colors='#533b28',linewidths=.42,alpha=.75))
    if kind in ('points','overlay'):
        if kind=='points':ax.scatter(*cloud.T,c=cloud[:,2],cmap='viridis',s=.65,alpha=.85,depthshade=False,rasterized=True)
        else:ax.scatter(*cloud.T,c='#155ea5',s=.75,alpha=.55,depthshade=False,rasterized=True)
    lo=np.minimum(p.min(0),v.min(0));hi=np.maximum(p.max(0),v.max(0));span=hi-lo;center=(hi+lo)/2
    for setter,c,d in zip((ax.set_xlim,ax.set_ylim,ax.set_zlim),center,np.maximum(span,span.max()*.18)):
        setter(c-d*.54,c+d*.54)
    ax.set_box_aspect(np.maximum(span,span.max()*.18));ax.view_init(elev=28,azim=-58)
    ax.set_axis_off()

cards=[];review=[]
summary=plt.figure(figsize=(18,21),facecolor='#f2f5f7')
for position,row in enumerate(batch['samples'],1):
    dest=OUT/row['directory'];p=np.loadtxt(row['source']);model_path=dest/(row['source_id']+'.json')
    m=json.loads(model_path.read_text(encoding='utf8')) if row['status']=='mesh_exported' else None
    failed=[k for k,v in row.get('gates',{}).items() if not v]
    status='PROXY PASS' if row.get('accepted') else ('REVIEW REQUIRED' if m else 'BUILD FAILED')
    fig=plt.figure(figsize=(15,9),facecolor='#f7f9fb')
    for j,(kind,title) in enumerate([('points','Input XYZ (height colors)'),('mesh','Predicted mesh / structural edges'),('overlay','Aligned overlay (blue = input)')],1):
        ax=fig.add_subplot(2,3,j,projection='3d');render3d(ax,p,m,kind);ax.set_title(title,pad=0)
    cloud=point_subset(p);edges=structural_edges(m) if m else []
    for j,(a,b,title) in enumerate([(0,1,'Top / XY'),(0,2,'Facade / XZ'),(1,2,'Facade / YZ')],4):
        ax=fig.add_subplot(2,3,j);ax.scatter(cloud[:,a],cloud[:,b],c='#165ca1',s=.55,alpha=.45,rasterized=True)
        for e in edges:ax.plot(e[:,a],e[:,b],color='#d06420',lw=.75,alpha=.9)
        ax.set_aspect('equal',adjustable='datalim');ax.set_title(title+' : points + mesh edges');ax.grid(alpha=.15)
        ax.set_xlabel('XYZ'[a]);ax.set_ylabel('XYZ'[b])
    val=(f"P95 {row['point_p95']:.3f} | within 0.15: {row['point_coverage_0_15']:.1%} | outline IoU {row['outline_iou']:.3f}" if 'point_p95' in row else row.get('error',row.get('validation_error','')))
    fig.suptitle(f"{row['review_id']:02d}  |  train {row['source_id']}  |  {row['points']:,} points  |  {status}",x=.03,ha='left',fontsize=17,fontweight='bold')
    fig.text(.03,.015,val+'\nFailed gates: '+(', '.join(failed) or 'none / see report')+'   |   No GT: these are observation proxies, not CD/ECD.',fontsize=9)
    fig.subplots_adjust(left=.04,right=.98,top=.90,bottom=.12,wspace=.17,hspace=.18)
    fig.savefig(dest/'review.png',dpi=145);plt.close(fig)
    ax=summary.add_subplot(5,4,position,projection='3d');render3d(ax,p,m,'overlay')
    ax.set_title(f"{row['review_id']:02d} / {row['source_id']}  "+('PASS' if row.get('accepted') else 'REVIEW'),fontsize=11)
    rid=row['review_id'];folder=html.escape(row['directory']);ident=html.escape(row['source_id'])
    links=f'<a href="{folder}/{ident}.obj">OBJ</a> · <a href="{folder}/{ident}.json">几何与证据 JSON</a>' if m else f'<a href="{folder}/failure.txt">失败记录</a>'
    if (dest/'validation.json').exists() and m:links+=f' · <a href="{folder}/validation.json">验证报告</a>'
    cards.append(f'<article id="m{rid:02d}"><h2>{rid:02d} · 训练集 {ident} <span>{status}</span></h2><p>{html.escape(val)}</p><p>未通过：{html.escape(", ".join(failed) or "查看报告")}</p><a href="{folder}/review.png"><img loading="lazy" src="{folder}/review.png" alt="编号 {rid:02d} 点云与模型六视图"></a><p>{links}</p><label>检查记录<textarea data-id="{rid:02d}" placeholder="部位 + 问题，如：左侧附楼屋顶被抬高"></textarea></label></article>')
    review.append([f'{rid:02d}',row['source_id'],row['points'],status,row.get('point_p95',''),row.get('point_coverage_0_15',''),'; '.join(failed),'',''])
    print('VIEW',rid,flush=True)
summary.suptitle('BuildingWorld / 20 fixed training samples\nBlue = observed XYZ; orange/gray = candidate mesh | all require manual review',fontsize=20,y=.99)
summary.subplots_adjust(top=.94,bottom=.02,wspace=0,hspace=.08);summary.savefig(OUT/'contact_sheet.png',dpi=130);plt.close(summary)
with (OUT/'feedback.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['编号','训练文件ID','点数','状态','点面P95','0.15内比例','失败门槛','问题部位','修改意见']);w.writerows(review)
nav=' '.join(f'<a href="#m{r["review_id"]:02d}">{r["review_id"]:02d}</a>' for r in batch['samples'])
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>BuildingWorld · 20 栋检查</title><style>
body{font:16px/1.65 system-ui,"Microsoft YaHei",sans-serif;margin:0;background:#edf2f5;color:#1d3043}header,main{max-width:1350px;margin:auto;padding:24px}h1{font-size:30px;margin:0}article{background:white;border-radius:12px;padding:22px;margin:24px 0;box-shadow:0 3px 14px #1231}h2{margin:0}span{font-size:13px;color:#b44b22;margin-left:20px}img{width:100%;display:block}a{color:#135d94}nav{position:sticky;top:0;background:#173b52;padding:10px;z-index:2;text-align:center}nav a{display:inline-block;color:white;margin:0 10px}textarea{box-sizing:border-box;width:100%;min-height:74px;margin-top:8px;padding:12px;font:inherit}button{padding:10px 18px;font:inherit;border:0;background:#176286;color:white;border-radius:6px;cursor:pointer}.notice{background:#fff3d8;padding:16px;border-radius:8px}</style>
<header><h1>BuildingWorld · 固定 20 栋训练样例</h1><p>算法版本 VERSION · 输入 XYZ → OBJ · 编号固定，失败不换样本。</p><div class="notice">这些是待检查的原型结果。保留复杂形状，但部分屋面分区、墙体高差和网格拓扑仍不正确。当前没有真值，所有点面距离和轮廓指标都不是官方 CD / ECD，也没有 FINAL SCORE。</div><p>每栋上排：输入、网格、叠加；下排：XY、XZ、YZ。蓝点来自输入，橙线为网格结构边。点击图片可放大。Blender 文件含总览及逐栋场景、点云叠加开关。</p><p><a href="buildingworld_train20.blend">Blender 检查场景</a> · <a href="contact_sheet.png">20 栋总图</a> · <a href="feedback.csv">反馈 CSV</a> · <a href="../../BUILDING_RECONSTRUCTION_ALGORITHM.md">规则与算法说明</a></p><button onclick="download()">导出填写的反馈 JSON</button><p>填写内容尽可能自动暂存在本机浏览器；请用导出按钮保存。</p></header><nav>NAV</nav><main>CARDS</main><script>
for(const e of document.querySelectorAll('textarea')){try{e.value=localStorage.getItem('bw20-'+e.dataset.id)||''}catch{}e.addEventListener('input',()=>{try{localStorage.setItem('bw20-'+e.dataset.id,e.value)}catch{}})}
function download(){const feedback=[...document.querySelectorAll('textarea')].map(e=>({review_id:e.dataset.id,comment:e.value}));const url=URL.createObjectURL(new Blob([JSON.stringify({batch:'train20-20260920',feedback},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='buildingworld_train20_feedback.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
</script></html>'''
(OUT/'index.html').write_text(page.replace('VERSION',batch['engine_version']).replace('NAV',nav).replace('CARDS',''.join(cards)).replace('train20-20260920',OUT.name),encoding='utf8')
print('CATALOGUE COMPLETE',flush=True)
