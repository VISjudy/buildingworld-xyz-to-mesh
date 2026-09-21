"""Freeze discovery-only evidence and explicit knowledge/image ablation inputs."""
from pathlib import Path
import importlib.util
import shutil
import os
import sys
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from harness.io import read_json,write_json,read_obj,read_points,sha256
from harness.evaluate import structure_edges,sample_lines
OLD=ROOT/'work/experiments/2026-09-21/starter78-feedback-pilot'
OUT=ROOT/'work/experiments/2026-09-21/feedback-components-v002'
OUT.mkdir(parents=True,exist_ok=True)
os.environ['MPLCONFIGDIR']=str(OUT/'matplotlib-diagnostics')
sys.dont_write_bytecode=True
SPEC=read_json(OLD/'setup/discovery.json')
base=ROOT/'releases/v0.1.0-starter78-standard-v001/source/algorithm.py'
spec=importlib.util.spec_from_file_location('baseline_diagnostics',base)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
results={r['id']:r for r in read_json(OLD/'baseline/results.json')['samples']}
examples=[]
for s in SPEC['samples']:
    p=read_points(s['points']);n,curve=module.normals(p)
    stable=(np.abs(n[:,2])>.55)&(curve<.035)
    q25=float(np.quantile(p[:,2],.25));roof=stable&(p[:,2]>q25)
    tie=stable&(p[:,2]>=q25)
    gt=read_obj(s['gt_mesh']);r=results[s['id']]
    entry={'id':s['id'],'stratum':s['evaluation_stratum'],'status':r['status'],
        'point_count':len(p),'roof_candidates':int(roof.sum()),'inclusive_q25_candidates':int(tie.sum()),
        'baseline_required_support':max(60,int(roof.sum()*.075)),
        'input_z_range':[float(p[:,2].min()),float(p[:,2].max())],
        'GT_z_range_development_only':[float(gt['vertices'][:,2].min()),float(gt['vertices'][:,2].max())],
        'coordinate_note':'Z is canonical elevation relative to input bbox center; zero is not ground.',
        'rules_relevant':['K01','K02','K03','K04','K05','K06','K07','K08','K09']}
    if r['status']=='evaluated':
        ev=read_json(OLD/'baseline/samples'/s['id']/'evaluation.json')
        obj=read_obj(OLD/'baseline/samples'/s['id']/'model.obj')
        edges,_=structure_edges(obj);ge,_=structure_edges(gt)
        pred_samples=sample_lines(obj['vertices'],edges,4000,739)
        mids=gt['vertices'][ge].mean(1);dist,nearest=cKDTree(pred_samples).query(mids)
        worst=np.argsort(dist)[-3:][::-1]
        entry.update(metrics={k:r[k]for k in ['CD','ECD','NC','p95','V_Ratio','F_Ratio']},
          observed=ev['observed']['all_points_to_surface'],normal_proxy=ev['observed']['estimated_normal_alignment'],
          localized_residuals=ev['observed']['worst_points'][:3],
          structure_diagnostics=[{'gt_edge_id':int(i),'midpoint':mids[i].tolist(),'nearest_predicted_structure_point':pred_samples[nearest[i]].tolist(),'distance':float(dist[i])}for i in worst],
          topology={k:ev['topology'][k]for k in ['watertight','open_edges','nonmanifold_edges','inconsistent_winding_edges','degenerate_triangles']},
          inferred_base_z=float(obj['vertices'][:,2].min()),
          roof_vertical_support={'stable_candidate_count':int(stable.sum()),'quantiles_01_50_99':np.quantile(p[stable,2],[.01,.5,.99]).tolist() if stable.any() else None})
    else:entry['error']='No roof plane supported'
    examples.append(entry)
feedback={'version':'external-feedback-v002','scope':'discovery24 only; no selection or transfer outcomes',
    'evidence_layers':['all-input geometry','stable input normal proxy + GT NC','localized GT structure-edge mismatch','topology','rule applicability facts','GT comparison'],
    'limitations':['No scanner trajectory; no missing-return emptiness constraint.','No complete prediction self-intersection test.','Local normal confidence is a PCA proxy, not a calibrated uncertainty.','GT comparisons are development evidence, never runtime inputs.'],
    'cases':examples}
write_json(OUT/'feedback-v002.json',feedback)
old_rules=read_json(ROOT/'config/knowledge/rules.json')
knowledge={'version':'building-knowledge-v002','parent':'building-knowledge-v001','rules':old_rules['rules']+[
    {'id':'K09','claim':'Roof elevation is a Z coordinate; facade height is roof elevation minus a supported base elevation. An input bbox center does not establish ground.',
     'constraint':'hard_reporting_and_soft_guard','status':'coordinate_invariant_fact; detection thresholds remain hypotheses',
     'source':'docs/DATASET_METHODS_V001.md; height-audit/findings.md (discovery evidence only for candidate design)',
     'applicability':'Z-up coordinates with known shared transform; local stable roof support',
     'required_evidence':['coordinate provenance','stable local roof observations','trusted ground if available'],
     'counterexample':'Roof-only or elevated scans do not identify building base; legitimate high-elevation buildings must not trigger an absolute-Z rejection.',
     'operators':['roof_support','height_sanity_guard','base_completion'],
     'fallback':'Reject unsupported proposed height corrections and retain the original inference with uncertainty; do not set ground to zero or clamp by absolute Z.'}],
    'experiences':[
     {'id':'X01','claim':'A failure-gated operator and an observed-footprint operator target different failure modes.','evidence_scope':'Prior discovery24+selection24 only','counterexample':'Recovering cases did not change geometry on common successes; shape improvement did not recover failures.'},
     {'id':'X02','claim':'An experience policy can change without improving the algorithm.','evidence_scope':'Prior policy describes hypotheses; no new-task outcome is used here.','counterexample':'A proposed gate may never activate or leave the underlying support shortage unresolved.'}],
    'causal_warning':'This is an explicit rule/experience update; its benefit requires a matched no-explicit-knowledge condition.'}
write_json(OUT/'knowledge-v002.json',knowledge)
selected=[]
for source in ['real_zurich','synthetic_mini']:
    available=[r for r in examples if r['stratum']==source]
    good=sorted([r for r in available if r['status']=='evaluated'],key=lambda r:r['metrics']['CD'],reverse=True)
    bad=[r for r in available if r['status']!='evaluated']
    selected.append([good[0],bad[0] if bad else good[1]])
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
images=[]
for page,cases in enumerate(selected):
    canvas=Image.new('RGB',(1280,680),'white');draw=ImageDraw.Draw(canvas)
    for row,r in enumerate(cases):
        draw.text((8,row*340+5),r['id']+' | '+r['stratum'],fill='#20333f',font=font)
        for col,(role,view,label) in enumerate([('input','oblique','Input'),('baseline','oblique','Initial algorithm'),('reference','oblique','GT (development only)'),('baseline','top','Initial top view')]):
            draw.text((col*320+5,row*340+28),label,font=font,fill='#20333f')
            path=OLD/'renders'/f'{r["id"]}_{view}_{role}.png'
            if path.exists():canvas.paste(Image.open(path).convert('RGB'),(col*320,row*340+55))
            else:draw.text((col*320+40,row*340+170),'FAILED: no mesh',font=font,fill='#a4332b')
    name=f'discovery-evidence-{page+1}.png';canvas.save(OUT/name);images.append(name)
for arm,use_knowledge,use_images in [('text_no_k',False,False),('text_k',True,False),('full',True,True)]:
    dest=OUT/'proposals'/arm;dest.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(base,dest/'initial_algorithm.py')
    write_json(dest/'feedback.json',feedback)
    write_json(dest/'knowledge.json',knowledge if use_knowledge else {'version':'no-explicit-knowledge','rules':[],'experiences':[],'note':'The model still has its inherent prior knowledge.'})
    write_json(dest/'image_manifest.json',{'images':images if use_images else [],'purpose':'External geometry evidence, not aesthetic scoring','images_are_development_GT':True})
    if use_images:
        for name in images:shutil.copyfile(OUT/name,dest/name)
write_json(OUT/'preregistration.json',{'id':'feedback-components-v002','initial_source_sha256':sha256(base),
    'conditions':['text_no_k','text_k','full'],'comparison':'text_k vs text_no_k for explicit knowledge bundle; full vs text_k for added images',
    'feedback_source':'discovery24, numerical/geometric evidence identical in all conditions',
    'candidate_budget':1,'max_changed_lines':140,'tool_call_limit':10,'syntax_checks':1,'seed':739,
    'model':'same inherited runtime; exact snapshot and token counts unavailable','evaluation':'all78; selection24 reported separately, still adaptive development across this project',
    'knowledge_update':'K09 coordinate/height rule plus X01/X02 prior experience, conditional rather than absolute height thresholds',
    'image_information_limit':'Added image evidence, not strictly information-equivalent or token-matched; one candidate cannot establish a causal modality effect',
    'planned_but_not_completed':['remove geometry','remove normals','remove structure','remove topology','depth/normal raster maps','full prediction self-intersection'],
    'manual_engineering_comparator':'unmodified archived v0.5.1, same preprocessing; do not attribute its historical improvements to this Harness'})
print('Prepared 3 conditions; discovery-only evidence and 2 image mosaics.')
