from pathlib import Path
import json
import numpy as np
import pytest
import trimesh
from harness.io import read_obj, write_obj, read_points, write_json, triangulate
from harness.evaluate import evaluate, structure_edges
from harness.workflow import seal_release, verify_release, compare_runs
from harness.feedback import make_feedback
from harness.derive import derive_wireframe


def cube(path, offset=None):
    m=trimesh.creation.box()
    v=m.vertices+(np.zeros(3) if offset is None else offset)
    write_obj(path,v,m.faces.tolist())
    return v,m.faces.tolist()


def test_structural_edges_ignore_coplanar_diagonals(tmp_path):
    p=tmp_path/'cube.obj';cube(p)
    edges,_=structure_edges(read_obj(p))
    assert len(edges)==12


def test_local_reference_identity_and_ground_coordinates(tmp_path):
    p=tmp_path/'cube.obj';v,_=cube(p,np.array([538000.,6584000.,40.]))
    xyz=tmp_path/'p.xyz';np.savetxt(xyz,v)
    r=evaluate(p,xyz,gt_mesh=p)
    assert r['observed']['all_points_to_surface']['max']<1e-8
    assert r['local_reference']['CD']<1e-10
    assert r['local_reference']['ECD']<1e-10
    assert r['local_reference']['NC']==pytest.approx(1)
    assert all(v is None for v in r['official'].values())
    assert r['topology']['signed_volume']==pytest.approx(1)


def test_open_and_reversed_faces_detected(tmp_path):
    p=tmp_path/'cube.obj';v,f=cube(p)
    q=tmp_path/'open.obj';write_obj(q,v,f[:-1])
    assert len(evaluate(q)['topology']['open_edges'])==3
    f[0]=f[0][::-1];q=tmp_path/'reversed.obj';write_obj(q,v,f)
    assert evaluate(q)['topology']['inconsistent_winding_edges']


def test_wireframe_is_not_mesh_gt(tmp_path):
    p=tmp_path/'wf.obj';p.write_text('v 0 0 0\nv 1 0 0\nv 1 1 0\nl 1 2 3\n')
    with pytest.raises(ValueError,match='wireframe'):triangulate(read_obj(p))


def test_concave_triangulation_area(tmp_path):
    p=tmp_path/'L.obj';v=[[0,0,0],[2,0,0],[2,1,0],[1,1,0],[1,2,0],[0,2,0]]
    write_obj(p,v,[list(range(6))]);obj=read_obj(p);t,_=triangulate(obj)
    assert trimesh.Trimesh(obj['vertices'],t,process=False).area==pytest.approx(3)


def test_nonfinite_input_and_invalid_columns(tmp_path):
    p=tmp_path/'p.xyz';p.write_text('0 0 0\n1 1 1\nnan 2 2\n')
    with pytest.raises(ValueError):read_points(p)
    with pytest.raises(ValueError):read_points(p,(0,0,1))


def test_immutable_output_and_tamper_detection(tmp_path):
    r=tmp_path/'release';r.mkdir();(r/'source.py').write_text('original')
    seal_release(r);assert verify_release(r)['valid']
    with pytest.raises(FileExistsError):seal_release(r)
    (r/'source.py').write_text('changed');assert not verify_release(r)['valid']


def test_no_feedback_does_not_leak_scores_or_knowledge(tmp_path):
    p=tmp_path/'c.obj';cube(p);rp=tmp_path/'report.json';write_json(rp,evaluate(p))
    kp=tmp_path/'knowledge.json';write_json(kp,{'rules':[{'id':'K04','claim':'SECRET_RULE'}]})
    packet=make_feedback(rp,kp,tmp_path/'F0','F0')
    assert set(packet)=={'condition','instruction'}
    assert 'SECRET_RULE' not in json.dumps(packet)
    with pytest.raises(ValueError,match='images'):make_feedback(rp,kp,tmp_path/'F4','F4')


def test_comparison_rejects_input_mismatch(tmp_path):
    dirs=[]
    for i in range(3):
        d=tmp_path/str(i);d.mkdir();dirs.append(d)
        write_json(d/'results.json',{'samples':[{'id':'same','status':'failed','input_sha256':str(i)}]})
    with pytest.raises(ValueError,match='input'):compare_runs(*dirs)


def test_derivation_labels_inferred_faces(tmp_path):
    wf=tmp_path/'wf.obj';wf.write_text('v 0 0 2\nv 2 0 2\nv 2 2 2\nv 0 2 2\nl 1 2\nl 2 3\nl 3 4\nl 4 1\n')
    xyz=tmp_path/'p.xyz';np.savetxt(xyz,[[0,0,0],[2,2,0],[1,1,2]])
    result=derive_wireframe(wf,xyz,tmp_path/'derived')
    assert result['surface_faces']==1
    assert not result['is_official_mesh_gt']
    assert 'inferred_base' in result['face_provenance']
    r=evaluate(tmp_path/'derived/completed_hypothesis.obj')
    assert not r['topology']['open_edges']


def test_freeze_excludes_machine_bytecode(tmp_path, monkeypatch):
    from harness import workflow
    from types import SimpleNamespace
    run=tmp_path/'run';source=run/'source';source.mkdir(parents=True)
    (source/'algorithm.py').write_text('# frozen source')
    cache=source/'__pycache__';cache.mkdir();(cache/'algorithm.pyc').write_bytes(b'cache')
    write_json(run/'results.json',{'source_sha256':'test','samples':[]})
    write_json(run/'inputs.json',{'role':'synthetic_test','samples':[]})
    knowledge=tmp_path/'rules.json';write_json(knowledge,{'rules':[]})
    (tmp_path/'releases').mkdir()
    monkeypatch.setattr(workflow,'REPO',tmp_path)
    monkeypatch.setattr(workflow.subprocess,'run',lambda *a,**k:SimpleNamespace(stdout='numpy==2.5.3\n'))
    result=workflow.freeze_release(run,'test-v1',knowledge)
    assert not list(result.rglob('*.pyc'))
    assert workflow.verify_release(result)['valid']


def test_sealed_test_manifest_never_enters_evolution(tmp_path):
    from harness.workflow import run_batch
    manifest=tmp_path/'sealed.json';write_json(manifest,{'role':'sealed_test','samples':[]})
    with pytest.raises(ValueError,match='sealed'):run_batch(tmp_path/'a.py',manifest,tmp_path/'out')
    assert not (tmp_path/'out').exists()
