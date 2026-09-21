"""Add measured all-point residual and structure-edge diagnostics without re-scoring."""
from pathlib import Path
import csv
import os
import sys
ROOT=Path(__file__).resolve().parents[3]
WORK=ROOT/'work/experiments/2026-09-21/starter78-feedback-pilot'
os.environ['MPLCONFIGDIR']=str(WORK/'matplotlib-diagnostics')
sys.path.insert(0,str(ROOT))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from harness.io import read_json, read_obj, read_points, write_json
from harness.evaluate import prepare, closest, structure_edges
from harness.pilot_analysis import paired

OUT=ROOT/'reports/2026-09-21-starter78-feedback-pilot'
dest=OUT/'diagnostics';dest.mkdir(exist_ok=False)
arms=['baseline','F0','F3'];records={a:{r['id']:r for r in read_json(WORK/a/'results.json')['samples']} for a in arms}
spec=read_json(WORK/'setup/all78.json');comparisons=[];cards=[]
for index,s in enumerate(spec['samples']):
    bid=s['id'];p=read_points(s['points']);gt=read_obj(s['gt_mesh']);gtedges,_=structure_edges(gt)
    fig,axes=plt.subplots(2,3,figsize=(12,6.8),layout='constrained')
    for j,arm in enumerate(arms):
        ax,ex=axes[:,j]
        r=records[arm][bid]
        ex.add_collection(LineCollection(gt['vertices'][gtedges][:,:,:2],colors='#929fa7',linewidths=2,label='Reference'))
        if r['status']=='evaluated':
            obj=read_obj(WORK/arm/'samples'/bid/'model.obj');mesh,_,origin=prepare(obj)
            d,_=closest(mesh,p-origin)
            # Identical [0, 1] scale for every version and building; saturated distances still retained numerically.
            scatter=ax.scatter(p[:,0],p[:,1],c=d,vmin=0,vmax=1,cmap='magma',s=3,rasterized=True)
            edges,_=structure_edges(obj)
            ex.add_collection(LineCollection(obj['vertices'][edges][:,:,:2],colors='#087d89',linewidths=.8,label='Prediction'))
            ax.set_title(f'{arm} | P95={r["p95"]:.4f}')
        else:
            ax.text(.5,.5,'FAILED',transform=ax.transAxes,ha='center',color='#a63429');ax.set_title(arm)
        bounds=np.vstack([p,gt['vertices']])
        for axis in [ax,ex]:
            axis.set_aspect('equal');axis.set_xlim(bounds[:,0].min()-.5,bounds[:,0].max()+.5)
            axis.set_ylim(bounds[:,1].min()-.5,bounds[:,1].max()+.5);axis.set_xlabel('Canonical X');axis.set_ylabel('Y')
        ex.set_title('Structure edges: gray GT / teal prediction')
    fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0,1),cmap='magma'),ax=list(axes[0]),label='All-point to surface distance (display capped at 1)')
    fig.suptitle(bid,fontsize=10);filename=bid+'.png';fig.savefig(dest/filename,dpi=100);plt.close(fig)
    cards.append(f'<article><h2>{bid}</h2><img loading="lazy" src="{filename}" alt="{bid} all-point residuals and projected structure edges"></article>')
    previous,current=records['F0'][bid],records['F3'][bid]
    comparisons.append({'id':bid,'source':s['evaluation_stratum'],'F0_status':previous['status'],'F3_status':current['status'],
        **{f'F3_minus_F0_{k}':current[k]-previous[k] if current['status']==previous['status']=='evaluated' else None for k in ['CD','ECD','NC','p95']}})
    print(index+1,78,flush=True)
with (dest/'F3_vs_F0.csv').open('x',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(comparisons[0]));w.writeheader();w.writerows(comparisons)
write_json(dest/'F3_vs_F0.json',paired(list(records['F0'].values()),list(records['F3'].values())))
(dest/'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>逐栋几何诊断</title><style>body{max-width:1200px;margin:20px auto;padding:16px;font:16px/1.7 system-ui;color:#20333f}img{max-width:100%;height:auto}h2{font-size:16px;overflow-wrap:anywhere}article{border-top:1px solid #ccc;margin-top:24px}</style><a href="../index.html">返回阶段报告</a><h1>全部输入点残差与结构边投影</h1><p>上排：全部原始点对预测表面的真实距离，所有版本固定0–1分析单位色标，超过1饱和显示。下排：顶视结构边，灰色为参考、青色为预测；排除共面三角化边，包含底边。顶视投影隐藏高度差，不能单靠此图证明结构正确。失败保留空位。</p><p>F0/F3是平行候选，以下差值不是算法父子收益：<a href="F3_vs_F0.csv">逐栋差值CSV</a> · <a href="F3_vs_F0.json">分来源配对汇总</a></p>'''+''.join(cards),encoding='utf-8')
write_json(dest/'verification.json',{'buildings':len(spec['samples']),'all_input_points_used':True,'shared_distance_color_range':[0,1],
  'distance_units':'canonical, not metres','metric_scores_unchanged':True,'projection':'top view, height ambiguity retained'})
