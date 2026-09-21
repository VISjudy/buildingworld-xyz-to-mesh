"""Synthetic evidence test: one isolated outlier versus a coherent small fixture."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import pointcloud_to_mesh as engine
import numpy as np
x,y=np.meshgrid(np.arange(0,5,.2),np.arange(0,5,.2));roof=np.c_[x.ravel(),y.ravel(),np.full(x.size,3.)]
sx,sy=np.meshgrid(np.arange(2,2.41,.1),np.arange(2,2.41,.1));fixture=np.c_[sx.ravel(),sy.ravel(),np.full(sx.size,3.7)]
p=np.r_[roof,fixture,[[100.,100.,100.]]]
mask,report=engine.conservative_noise_mask(p)
assert not mask[-1],'Isolated distant point must be flagged'
assert mask[len(roof):-1].all(),'Coherent roof fixture must be retained'
off,off_report=engine.conservative_noise_mask(p,'off');assert off.all()
assert np.array_equal(p[-1],[100,100,100]),'Input must never be moved'
result={'isolated_point_flagged':True,'small_coherent_fixture_retained':True,'off_mode_retains_all':True,'input_coordinates_unchanged':True,'diagnostics':report,'scope':'Synthetic filter behavior only, not proof that real outliers are noise'}
(ROOT/'work/experiments/noise_review/filter_test.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))
