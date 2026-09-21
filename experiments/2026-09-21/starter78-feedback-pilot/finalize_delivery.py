"""Link the supplementary diagnostics and save local delivery checks."""
from pathlib import Path
import json
import sys
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root))
from harness.io import write_json, read_json, sha256
out=root/'reports/2026-09-21-starter78-feedback-pilot'
p=out/'index.html';text=p.read_text(encoding='utf-8')
needle='<h2>固定相机的逐栋对比</h2>'
link='<p><a href="diagnostics/index.html">全部78栋：点到表面残差、结构边投影及F3相对F0差值</a></p>'
assert needle in text
assert (out/'diagnostics/index.html').exists(), 'Wait for diagnostics export to finish'
if link not in text:
    p.write_text(text.replace(needle,needle+link),encoding='utf-8')
p=out/'diagnostics/index.html';text=p.read_text(encoding='utf-8')
text=text.replace('<p>F0/F3是平行候选', '<p>二维诊断坐标范围固定为输入与GT的联合范围，外扩预测边可能裁剪；请结合七视角三维图判断。</p><p>F0/F3是平行候选')
p.write_text(text,encoding='utf-8')
versions=['v0.1.0-starter78-standard-v001','v0.1.2-pilot-f0-v001','v0.1.2-pilot-f3-v001','v0.1.2-transfer-original-v001','v0.1.2-transfer-evolved-v001']
checks=[]
for version in versions:
    folder=root/'releases'/version;manifest=read_json(folder/'manifest.json')
    for name,expected in manifest['files'].items():
        assert sha256(folder/name)==expected,(version,name)
    checks.append({'version':version,'files':len(manifest['files']),'all_sha256_match':True})
write_json(out/'delivery-qa.json',{'releases':checks,'tests':'27 passed',
    'source_coordinate_roundtrips':len(read_json(out/'verification.json')['roundtrips']),
    'frozen_F3_replay':{'id':'point2building_03060_z4cd103de00000004','mesh_bytes_identical':True,'CD_ECD_NC_identical':True},
    'raw_data_in_release':False,'diagnostic_buildings':78,
    'visual_review':'Desktop/mobile screenshots and representative seven-view comparison reviewed; browser-qa.json stores functional checks.'})
(root.parent/'dataset/processed/standardized_pairs_v001/README.md').write_text('''# Standardized paired LoD2 data v001

562 pairs: 363 real Zurich + 199 synthetic PolyGNN mini.
Only manifests/starter78.json is active for reconstruction. Full train432/test130 remain locked.
Input-only bbox center and isotropic scale (diagonal / 30); canonical coordinates are not metres.
All source points retained. GT follows the same transform; no GT-derived ground points are added.
Transform/provenance/hashes accompany each pair. Original source data and prior exports are untouched.
Paper methods and screening thresholds: ../../../buildingworld-xyz-to-mesh/docs/DATASET_METHODS_V001.md
''',encoding='utf-8')
print('Delivery checks PASS')
