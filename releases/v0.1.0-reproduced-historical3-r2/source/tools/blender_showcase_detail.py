"""Reuse the presentation only; import the V2 geometry into a separate scene."""
from pathlib import Path
source=Path('F:/codex/building/scripts/buildingworld/blender_showcase.py').read_text(encoding='utf8')
replacements={
    'lod2_xyz_baseline':'lod2_xyz_detail',
    'BuildingWorld_XYZ_Prototype':'BuildingWorld_XYZ_DetailV2',
    'BW_':'BWv2_',
    '_LOD2_prototype':'_LOD2_detail',
    'buildingworld_xyz_prototype.blend':'buildingworld_xyz_detail.blend',
    "{'roof':0,'wall':1,'ground_assumed':2}[sem]":"(2 if sem=='ground_assumed' else (0 if sem in ['roof','roof_fixture'] else 1))",
    "('GABLE' if number=='2000' else 'FLAT')":"{'10':'REENTRANT','1000':'ROOF FIXTURE','2000':'STEPPED ROOF'}[number]",
    'BuildingWorld | XYZ-only reconstruction':'BuildingWorld | Contour-faithful reconstruction',
    'Fitted roof / completed walls / provisional base':'Local roofs / observed setbacks / inferred wall continuation',
    'XYZ-only geometric baseline; provisional ground; no GT evaluation.':'Local roof domains and observed facade constraints; provisional ground; no GT evaluation.'
}
for old,new in replacements.items():
    if old not in source:raise RuntimeError('Presentation template changed: '+old)
    source=source.replace(old,new)
exec(compile(source,'blender_showcase_detail_generated','exec'))
