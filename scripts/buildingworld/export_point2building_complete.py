"""Preserve all qualifying real pairs and freeze a starter-isolated future split."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial.distance import pdist

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.data_splits import grouped_holdout
from harness.io import read_json, read_obj, sha256, write_json
from export_facade_pairs import export


def key(row):
    return row['city'], row['split'], row['id']


def curate(audit_file, topology_file, blender_file, starter_file, output):
    audit = read_json(audit_file)
    topology = read_json(topology_file)
    blender = read_json(blender_file)
    starter = read_json(starter_file)
    catalog = read_json(Path(audit_file).parent / 'catalog.json')['pairs']
    screened = {key(r): r for r in topology['results']}
    audited = {key(r): r for r in audit['results']}
    checks = {key(r): r for r in blender['results']}
    if set(screened) != {key(r) for r in catalog} or len(screened) != len(catalog):
        raise ValueError('Topology screen must cover the entire paired catalog uniquely')
    if {k for k, r in screened.items() if r['closed_consistent']} != set(audited):
        raise ValueError('Full audit must cover every topology-qualified pair')
    if blender['input_audit_sha256'] != sha256(audit_file):
        raise ValueError('Blender audit belongs to a different input')
    selected = [r for r in audit['results'] if r.get('selected_for_facade_development')]
    if set(checks) != {key(r) for r in selected}:
        raise ValueError('Missing independent Blender checks')
    # Never silently export an invalid reference. Preserve failed QA for review.
    for row in selected:
        if not checks[key(row)]['pass'] or checks[key(row)]['mesh_sha256'] != row['mesh_sha256']:
            raise ValueError('Independent mesh check failed: ' + row['id'])
        if sha256(row['points']) != row['points_sha256'] or sha256(row['mesh']) != row['mesh_sha256']:
            raise ValueError('Source changed since audit: ' + row['id'])
    if len(starter['samples']) != 78:
        raise ValueError('This project stage requires the frozen 78-pair starter manifest')
    starter_real = {r['id'] for r in starter['samples'] if r['dataset'] == 'point2building'}
    if not starter_real <= {r['id'] for r in selected}:
        raise ValueError('Starter reference no longer passes fixed QA; explicit correction needed')
    shape_rows = []
    for row in selected:
        vertices = read_obj(row['mesh'])['vertices']
        shape_rows.append({'id': row['id'], 'center_xy': row['author_transform']['center'][:2],
                           'mesh_sha256': row['mesh_sha256'],
                           'shape_distances': np.sort(pdist(vertices) * row['author_transform']['scale'])})
    split = grouped_holdout(shape_rows, starter_real)
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    export([audit_file], out / 'pairs', max_per_split=0)
    exported = read_json(out / 'pairs/manifest.json')['samples']
    manifests = out / 'manifests'
    manifests.mkdir()
    for r in exported:
        r['project_split'] = split['assignment'][r['id']]
        r['spatial_similarity_group'] = split['group_ids'][r['id']]
        r['starter_overlap'] = r['id'] in starter_real
        r['sha256'] = r['point_sha256']
        r['localize'] = True
        r['columns'] = [0, 1, 2]
        r['gt_wireframe'] = str(Path(r['gt_mesh']).with_name('wireframe.obj'))
    for name in ['train', 'test']:
        write_json(manifests / ('project_' + name + '.json'), {
            'role': 'deferred_train' if name == 'train' else 'sealed_test',
            'stage_locked': True, 'reconstruction_testing_authorized_now': False,
            'samples': [r for r in exported if r['project_split'] == name],
            'split_scope': 'project holdout from author-train; not the author benchmark',
            'unlock_requires': 'Document stability on starter78 and freeze algorithm, evaluator, config and acceptance record. No automatic unlock.',
        })
    for name in ['trainset', 'testset']:
        write_json(manifests / ('author_' + name + '.json'), {
            'role': 'author_split_inventory', 'stage_locked': True,
            'samples': [r for r in exported if r['author_split'] == name],
            'warning': 'Author test IDs already in starter development cannot be claimed unseen.'})
    starters = []
    for r in starter['samples']:
        if sha256(r['points']) != r['point_sha256'] or sha256(r['gt_mesh']) != r['mesh_sha256']:
            raise ValueError('Starter file changed')
        starters.append({**r, 'source_id': r['id'], 'id': r['dataset'] + '_' + r['id'],
                         'sha256': r['point_sha256'], 'localize': True, 'columns': [0, 1, 2],
                         'gt_wireframe': str(Path(r['gt_mesh']).with_name('wireframe.obj'))})
    write_json(manifests / 'starter78_development.json', {
        'role': 'development', 'samples': starters, 'source_manifest_sha256': sha256(starter_file),
        'note': 'All 78 are development samples, including those originally labeled author test. Separate real and simulated results.'})
    decisions = []
    for row in catalog:
        reasons = []
        if not screened[key(row)]['closed_consistent']:
            reasons.append('strict_closed_consistent_nondegenerate_topology_not_passed')
        else:
            r = audited[key(row)]
            if r['status'] != 'audited':
                reasons.append('audit_error')
            else:
                if not r['facade_observation_pass']:
                    reasons.append('insufficient_observed_facade_support')
                if not r['closed_wall_base_mesh_pass']:
                    reasons.append('closed_wall_base_requirement_not_passed')
                if r['p95_fraction_diagonal'] > .05:
                    reasons.append('point_reference_p95_exceeds_fixed_threshold')
        decisions.append({'city': row['city'], 'author_split': row['split'], 'id': row['id'],
                          'retained_in_raw': True, 'retained_in_quality_set': not reasons,
                          'reasons': reasons})
    if sum(r['retained_in_quality_set'] for r in decisions) != len(exported):
        raise ValueError('Decision ledger does not match exported population')
    write_json(out / 'quality_decisions.json', {'rows': decisions})
    write_json(out / 'split_groups.json', split)
    # Check saved contents rather than counting output directories as proof.
    for row in exported:
        if sha256(row['points']) != row['point_sha256'] or sha256(row['gt_mesh']) != row['mesh_sha256']:
            raise ValueError('Export hash verification failed')
    test_ids = {r['id'] for r in exported if r['project_split'] == 'test'}
    assert not test_ids & starter_real
    counts = dict(Counter(r['project_split'] for r in exported))
    summary = {
        'raw_pairs': len(catalog), 'topology_pass': len(audited), 'facade_joint_pass': len(selected),
        'blender_pass': blender['passed'], 'exported_pairs': len(exported),
        'author_split_counts': dict(Counter(r['author_split'] for r in exported)),
        'project_split_counts': counts, 'starter78_count': len(starters),
        'starter_real_overlap': len(starter_real), 'test_starter_overlap': 0,
        'author_test_starter_overlap': sum(r['author_split'] == 'testset' and r['starter_overlap'] for r in exported),
        'test_author_split_counts': dict(Counter(r['author_split'] for r in exported if r['project_split'] == 'test')),
        'rejection_reason_counts_nonexclusive': dict(Counter(reason for r in decisions for reason in r['reasons'])),
        'split_group_count': len(split['groups']), 'test_group_count': split['test_group_count'],
        'similarity_link_count': len(split['shape_similarity_links']),
        'minimum_train_test_center_distance_source_units': split['minimum_train_test_center_distance_source_units'],
        'split_policy': split['policy'], 'quality_thresholds': audit['thresholds'],
        'input_hashes': {name: sha256(p) for name, p in [('audit', audit_file), ('topology', topology_file),
                         ('blender', blender_file), ('starter', starter_file)]},
        'manifest_hashes': {p.name: sha256(p) for p in sorted(manifests.glob('*.json'))},
        'reconstruction_runs_on_full_set': 0, 'current_stage': 'starter78_development_only',
        'quality_selection_is_not_unbiased': True,
        'limitations': [blender['limitation'], 'CRS and vertical datum not independently established',
                       'Shape grouping is not exhaustive near-duplicate detection',
                       'Project holdout comes from author train; published pretrained Point2Building weights may have seen it',
                       'Single-city quality-selected subset; no cross-city or full-distribution claim'],
    }
    write_json(out / 'summary.json', summary)
    (out / 'README.md').write_text(f'''# Point2Building 完整质量筛选集 v001

全部 {len(catalog):,} 对原始数据均保留在 ../../external/point2building/raw/。严格拓扑预筛后审核全部 {len(audited)} 对，导出 {len(exported)} 对，无数量截断。这里的“高质量”限定为已执行的固定数据 QA，不保证语义完美或全面无自交。

- pairs/：每对 XYZ、作者参考 Mesh、派生线框、坐标与哈希记录；按作者原 trainset/testset 存放。
- manifests/author_*.json：原作者划分，仅作清单。
- manifests/project_train.json：{counts['train']} 对，含 {len(starter_real)} 对已指定真实入门样例；新增训练数据暂缓使用。
- manifests/project_test.json：{counts['test']} 对，封存；与入门样例 ID/空间邻近组/当前几何相似组隔离。
- manifests/starter78_development.json：目前唯一允许用于算法迭代的 78 对入口，指向原有文件。
- quality_decisions.json：全部原始配对的保留/未通过原因，不删除原始数据。
- split_groups.json：确定性的空间/相似组与划分，不依赖任何算法预测。

全部 18 对符合当前质量门槛的作者 test 已在入门组；项目封存组来自作者 train，并非作者标准测试集。使用作者预训练权重比较时存在训练重叠风险，需按项目划分重训或另用作者标准评测协议。

遵守用户阶段安排：先在固定 78 对上迭代稳定并冻结算法、评测器和配置，登记阶段验收后再开启完整集测试。此次仅数据 QA；未在完整集运行重建或评分。训练／测试清单角色均阻止当前演化批处理直接载入。公开 Git 仅保存脚本与审核摘要，不上传数据。
''', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['audit-file', 'topology-file', 'blender-file', 'starter-file', 'output']:
        parser.add_argument('--' + name, required=True)
    curate(**vars(parser.parse_args()))
