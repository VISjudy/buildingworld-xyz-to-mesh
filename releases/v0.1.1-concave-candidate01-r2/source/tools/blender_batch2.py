"""Create the second review scene without changing first-batch geometry."""
from pathlib import Path
source=Path('F:/codex/building/scripts/buildingworld/blender_train20.py').read_text(encoding='utf8')
for old,new in {
    'work/experiments/train20_review':'work/experiments/train20_batch2',
    'BuildingWorld_Train20_Review':'BuildingWorld_Batch2_21_40',
    'T20_':'B02_',
    'for row in batch[\'samples\']:':'for position,row in enumerate(batch[\'samples\'],1):',
    '((idx-1)%4-1.5)':'((position-1)%4-1.5)',
    '(4-(idx-1)//4)':'(4-(position-1)//4)',
    "'BUILDINGWORLD / 20 TRAINING SAMPLES'":"'BUILDINGWORLD / BATCH 02 / SAMPLES 21-40'",
    "f'Inspect_{idx:02d}_train_{ident}'":"f'Inspect_{idx:02d}_train_{ident}'"
}.items():source=source.replace(old,new)
exec(compile(source,'blender_batch2_generated','exec'))
