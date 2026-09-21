"""Index complete local real/simulated quality sets without duplicating original files."""
import argparse
from collections import Counter
from pathlib import Path
import sys
import numpy as np
from scipy.spatial.distance import pdist

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.io import read_json, read_obj, sha256, write_json
from harness.data_splits import author_holdout_without_starters


def build(real_root, synthetic_root, synthetic_raw, synthetic_audit, blender_audit, starter, output):
    real_root, synthetic_root, synthetic_raw = map(Path, [real_root, synthetic_root, synthetic_raw])
    audit, blender, starter_spec = map(read_json, [synthetic_audit, blender_audit, starter])
    if audit['kind'] != 'polygnn_mini' or audit['audited_count'] != audit['catalog_pair_count']:
        raise ValueError('Expected exhaustive local mini audit')
    rows = read_json(synthetic_root / 'pairs/manifest.json')['samples']
    valid = {r['id']: r for r in audit['results'] if r.get('selected_for_facade_development')}
    checks = {r['id']: r for r in blender['results']}
    if {r['id'] for r in rows} != set(valid) or set(checks) != set(valid):
        raise ValueError('Exports/checks must cover every qualifying synthetic pair')
    if blender['input_audit_sha256'] != sha256(synthetic_audit):
        raise ValueError('Independent checks refer to another audit')
    extraction = read_json(synthetic_raw / 'extraction_manifest.json')
    for r in extraction['files']:
        p = synthetic_raw / r['path']
        if p.stat().st_size != r['bytes'] or sha256(p) != r['sha256']:
            raise ValueError('Raw synthetic file integrity mismatch: ' + r['path'])
    shape_rows = []
    for r in rows:
        v = valid[r['id']]
        if not checks[r['id']]['pass'] or checks[r['id']]['mesh_sha256'] != v['mesh_sha256']:
            raise ValueError('Blender check failed')
        if sha256(v['points']) != v['points_sha256'] or sha256(v['mesh']) != v['mesh_sha256']:
            raise ValueError('Audited source changed')
        if sha256(r['points']) != r['point_sha256'] or sha256(r['gt_mesh']) != r['mesh_sha256']:
            raise ValueError('Exported pair changed')
        shape_rows.append({**r, 'shape_distances': np.sort(pdist(read_obj(r['gt_mesh'])['vertices']))})
    starter_sim = {r['id'] for r in starter_spec['samples'] if r['dataset'] == 'polygnn_mini'}
    split = author_holdout_without_starters(shape_rows, starter_sim)
    all_rows = []
    for name in ['train', 'test']:
        spec = read_json(real_root / ('manifests/project_' + name + '.json'))
        if not spec['stage_locked']:
            raise ValueError('Real collection must remain locked')
        all_rows.extend(spec['samples'])
    for r in rows:
        r.update(project_split=split['assignment'][r['id']],
                 spatial_similarity_group=split['group_ids'][r['id']],
                 starter_overlap=r['id'] in starter_sim, localize=True, columns=[0, 1, 2],
                 sha256=r['point_sha256'], gt_wireframe=str(Path(r['gt_mesh']).with_name('wireframe.obj')))
    # Keep immutable component exports. Only new collection metadata is written.
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifests = out / 'manifests'
    manifests.mkdir()
    all_rows.extend(rows)
    for r in all_rows:
        if sha256(r['points']) != r['point_sha256'] or sha256(r['gt_mesh']) != r['mesh_sha256']:
            raise ValueError('Collection content hash mismatch')
        r['source_id'] = r['id']
        r['id'] = r['dataset'] + '_' + r['id']
        r['evaluation_stratum'] = 'real_zurich' if r['dataset'] == 'point2building' else 'synthetic_mini'
    if len({r['id'] for r in all_rows}) != len(all_rows):
        raise ValueError('Collection ID collision')
    ids_by_split = {k: {r['id'] for r in all_rows if r['project_split'] == k} for k in ['train', 'test']}
    starter_ids = {r['dataset'] + '_' + r['id'] for r in starter_spec['samples']}
    if not starter_ids <= ids_by_split['train'] or starter_ids & ids_by_split['test']:
        raise ValueError('All starter samples must be in project training')
    for field in ['id', 'point_sha256', 'mesh_sha256', 'spatial_similarity_group']:
        if ({r[field] for r in all_rows if r['project_split'] == 'train'}
                & {r[field] for r in all_rows if r['project_split'] == 'test'}):
            raise ValueError('Cross-split overlap: ' + field)
    for stratum in ['all', 'real_zurich', 'synthetic_mini']:
        for name in ['train', 'test']:
            write_json(manifests / (stratum + '_' + name + '.json'), {
                'role': 'deferred_train' if name == 'train' else 'sealed_test',
                'stage_locked': True, 'reconstruction_testing_authorized_now': False,
                'evaluation_policy': 'Report each source separately; never pool metric distances across coordinate units',
                'samples': [r for r in all_rows if r['project_split'] == name
                            and (stratum == 'all' or r['evaluation_stratum'] == stratum)]})
    for name in ['trainset', 'testset']:
        write_json(manifests / ('synthetic_author_' + name + '.json'), {
            'role': 'author_split_inventory', 'stage_locked': True,
            'samples': [r for r in rows if r['author_split'] == name]})
    dev = read_json(real_root / 'manifests/starter78_development.json')
    if {r['id'] for r in dev['samples']} != starter_ids:
        raise ValueError('Starter manifest identity mismatch')
    for r in dev['samples']:
        if sha256(r['points']) != r['point_sha256'] or sha256(r['gt_mesh']) != r['mesh_sha256']:
            raise ValueError('Starter file integrity mismatch')
    write_json(manifests / 'starter78_development.json', dev)
    write_json(out / 'synthetic_split_groups.json', split)
    write_json(out / 'synthetic_quality_decisions.json', {
        'raw_preserved': True, 'rows': [{'id': r['id'], 'author_split': r['split'],
            'qualified': bool(r.get('selected_for_facade_development')),
            'facade_observation_pass': r.get('facade_observation_pass'),
            'closed_wall_base_mesh_pass': r.get('closed_wall_base_mesh_pass'),
            'p95_fraction_diagonal': r.get('p95_fraction_diagonal'),
            'status': r['status']} for r in audit['results']]})
    sources = {}
    for name in ['real_zurich', 'synthetic_mini']:
        selected = [r for r in all_rows if r['evaluation_stratum'] == name]
        sources[name] = {'qualified_pairs': len(selected),
                         'project_splits': dict(Counter(r['project_split'] for r in selected)),
                         'author_splits': dict(Counter(r['author_split'] for r in selected)),
                         'starter_overlap': sum(r['starter_overlap'] for r in selected)}
    summary = {'scope': 'all qualifying pairs in locally downloaded Zurich + PolyGNN mini packages',
               'upstream_munich_full_included': False,
               'scope_authorization': 'User explicitly selected local mini only for this round on 2026-09-21',
               'sources': sources, 'total_quality_pairs': len(all_rows),
               'project_splits': dict(Counter(r['project_split'] for r in all_rows)),
               'starter78_count': len(starter_ids), 'starter_test_overlap': 0,
               'synthetic_raw_pairs': audit['catalog_pair_count'],
               'synthetic_raw_files_verified': len(extraction['files']),
               'synthetic_blender_pass': blender['passed'],
               'synthetic_similarity_links': len(split['similarity_links']),
               'synthetic_spatial_independence': 'not established; original coordinates unavailable in mini',
               'full_collection_reconstruction_runs': 0,
               'input_hashes': {n: sha256(p) for n, p in [('synthetic_audit', synthetic_audit),
                     ('blender_audit', blender_audit), ('starter', starter),
                     ('real_summary', real_root / 'summary.json')]},
               'manifest_hashes': {p.name: sha256(p) for p in manifests.glob('*.json')}}
    write_json(out / 'manifest.json', {'role': 'quality_collection_inventory', 'stage_locked': True,
                                     'sources': sources, 'samples': all_rows})
    write_json(out / 'summary.json', summary)
    (out / 'README.md').write_text(f'''# 完整本地配对集合 v001

本轮范围经用户确认：Zurich 真实采集 + 已下载 PolyGNN mini 的全部合格仿真配对。不含尚未下载的 Munich 完整发布版。

共 {len(all_rows)} 对：真实 363 对、仿真 {len(rows)} 对。每条清单指向已有数据文件，统一归档不重复复制大文件。

- 真实文件：../point2building_hq_v001/pairs/，源坐标已共同还原，CRS 尚未独立核准。
- 仿真文件：../polygnn_mini_hq_v001/pairs/，保留归一化坐标，不能标为米；从作者原始数值 NPY 导出 XYZ。
- manifests/real_zurich_* 与 synthetic_mini_*：分别提供训练/测试入口；all_* 仅作为统一编排清单，评测不得混报。
- manifests/starter78_development.json：固定 78 对当前开发入口，原数据未改写。
- 原作者标签另存，项目测试剔除已用于入门的作者 test 及与训练/入门几何相似的组。

本轮仅入库与数据 QA，未执行完整集合重建。先在 78 对上迭代稳定并冻结，再开启完整集；训练和测试清单均带阶段锁。质量筛选与有限相交检查不构成全面语义或自交证明。mini 的全量合格集不等于整个 PolyGNN Munich 发布库。
''', encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ['real-root', 'synthetic-root', 'synthetic-raw', 'synthetic-audit', 'blender-audit', 'starter', 'output']:
        p.add_argument('--' + name, required=True)
    build(**vars(p.parse_args()))
