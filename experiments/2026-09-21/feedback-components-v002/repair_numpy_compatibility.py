"""Preserve a failed proposal and make a documented, algebraically equal API repair."""
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from harness.io import write_json,sha256
p=ROOT/'work/experiments/2026-09-21/feedback-components-v002/proposals'
old=p/'text_no_k';new=p/'text_no_k_compat';new.mkdir(exist_ok=False)
for f in old.iterdir():
    if f.is_file():shutil.copyfile(f,new/f.name)
source=old/'candidate.py'
code=source.read_text(encoding='utf-8')
before='np.sum(np.cross(footprint,np.roll(footprint,-1,axis=0)))'
after='np.sum(footprint[:,0]*np.roll(footprint[:,1],-1)-footprint[:,1]*np.roll(footprint[:,0],-1))'
assert code.count(before)==1
(new/'candidate.py').write_text(code.replace(before,after),encoding='utf-8')
write_json(new/'compatibility.json',{'original_candidate_sha256':sha256(source),'repaired_candidate_sha256':sha256(new/'candidate.py'),
    'trigger':'NumPy 2.5.3 rejects 2-component np.cross vectors; original proposal failed at footprint orientation.',
    'change':'Replace scalar 2D cross product sum by identical shoelace determinant; one expression only.',
    'not_model_feedback_iteration':True,'no_geometry_threshold_changed':True,'no_ground_truth_used':True,
    'raw_failures_preserved':'text_no_k/results.json',
    'experimental_limit':'Post-proposal runtime compatibility repair; report raw and repaired conditions separately, not a clean preregistered zero-repair arm.'})
print('Compatibility-only candidate recorded; original unchanged.')
