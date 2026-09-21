import io
import json
import tarfile
import numpy as np
import pytest
import trimesh
from harness.io import write_obj
from scripts.buildingworld.analyze_paired_building_data import audit_pair,extract
from scripts.buildingworld.check_project_memory import validate


def test_facade_audit_does_not_confuse_roof_edge_with_wall(tmp_path):
    m=trimesh.creation.box();mesh=tmp_path/'gt.obj';write_obj(mesh,m.vertices,m.faces.tolist())
    roof=np.array([[x,y,.5] for x in np.linspace(-.5,.5,11) for y in [-.5,0,.5]])
    points=tmp_path/'roof.xyz';np.savetxt(points,roof)
    row={'points':str(points),'mesh':str(mesh)}
    r=audit_pair(row);assert r['facade_points']==0 and not r['facade_observation_pass']
    wall=np.array([[.5,y,z] for y in [-.2,0,.2] for z in np.linspace(-.35,.35,10)])
    points2=tmp_path/'wall.xyz';np.savetxt(points2,np.vstack([roof,wall]))
    r=audit_pair({**row,'points':str(points2)})
    assert r['facade_points']==30 and r['selected_for_facade_development']


def test_archive_rejects_path_escape(tmp_path):
    p=tmp_path/'bad.tar.gz'
    with tarfile.open(p,'w:gz') as t:
        item=tarfile.TarInfo('../escape.obj');item.size=1;t.addfile(item,io.BytesIO(b'x'))
    with pytest.raises(ValueError,match='Unsafe'):extract(p,tmp_path/'out','polygnn_mini')
    assert not (tmp_path/'escape.obj').exists()


def test_memory_validator_rejects_missing_evidence(tmp_path):
    files=['memory.md','AGENTS.md','PROJECT_MEMORY.md','prompt/INDEX.md','prompt/registers/research.md',
           'prompt/registers/datasets.md','prompt/protocols/memory-management.md','prompt/knowledge/experience-index.md','experiments/INDEX.md']
    for name in files:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('memory.md',encoding='utf-8')
    r={k:'x' for k in ['id','date','kind','claim','conditions','counterexamples','next_action']}
    r.update(status='hypothesis',evidence=['missing.json'])
    (tmp_path/'prompt/knowledge/experiences.jsonl').write_text(json.dumps(r),encoding='utf-8')
    assert any('evidence' in error for error in validate(tmp_path))
