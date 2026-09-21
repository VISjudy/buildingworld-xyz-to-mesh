"""Deterministic project holdout groups, using data identity/geometry and never predictions."""
import hashlib
import math
import numpy as np
from scipy.spatial import cKDTree


def author_holdout_without_starters(rows, starter_ids):
    """Retain unused author-test groups, moving exposed/similar groups to train.

    For normalized mini data, no source XY exists: never invent spatial isolation.
    Distances must use that dataset's normalized coordinates, not physical metres.
    """
    rows = sorted(rows, key=lambda r: r['id'])
    ids = {r['id'] for r in rows}
    if len(ids) != len(rows) or not set(starter_ids) <= ids:
        raise ValueError('Unique IDs and known starter membership required')
    if any(r['author_split'] not in ['trainset', 'testset'] for r in rows):
        raise ValueError('Unknown author split')
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    links = []
    for i, row in enumerate(rows):
        a = np.asarray(row['shape_distances'])
        for j in range(i):
            b = np.asarray(rows[j]['shape_distances'])
            if (row['mesh_sha256'] == rows[j]['mesh_sha256']
                    or row['point_sha256'] == rows[j]['point_sha256']
                    or (a.size and a.shape == b.shape and np.allclose(a, b, atol=1e-6, rtol=1e-4))):
                x, y = find(i), find(j)
                parent[max(x, y)] = min(x, y)
                links.append([rows[j]['id'], row['id']])
    groups = {}
    for i, row in enumerate(rows):
        groups.setdefault(find(i), []).append(row)
    assignment, group_ids = {}, {}
    for group in groups.values():
        exposed = any(r['id'] in starter_ids or r['author_split'] == 'trainset' for r in group)
        group_id = 'sim_group_' + hashlib.sha256('|'.join(r['id'] for r in group).encode()).hexdigest()[:16]
        for r in group:
            assignment[r['id']] = 'train' if exposed else 'test'
            group_ids[r['id']] = group_id
    return {'assignment': assignment, 'group_ids': group_ids, 'similarity_links': links,
            'policy': {'keep_unexposed_author_test': True, 'starter_excluded_from_test': True,
                       'shape_atol_normalized_units': 1e-6, 'shape_rtol': 1e-4,
                       'spatial_isolation': 'not_established_source_coordinates_unavailable',
                       'near_duplicate_check': 'conservative_proxy_not_exhaustive'}}


def grouped_holdout(rows, starter_ids, separation=200., test_fraction=.2):
    """Rows contain id, center_xy, shape_distances and mesh_sha256.

    Shape distances are sorted vertex-pair distances in source units. They are a
    conservative similarity proxy, not a proof that distinct buildings are equal.
    Nearby/similar components remain together; starter components remain train.
    """
    if not rows or not 0 < test_fraction < 1 or separation <= 0:
        raise ValueError('Nonempty rows, positive separation and 0 < test fraction < 1 required')
    rows = sorted(rows, key=lambda r: r['id'])
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate building IDs')
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def join(i, j):
        a, b = find(i), find(j)
        parent[max(a, b)] = min(a, b)

    xy = np.array([r['center_xy'] for r in rows], dtype=float)
    if xy.shape != (len(rows), 2) or not np.isfinite(xy).all():
        raise ValueError('Finite author XY coordinates required')
    spatial_links = sorted(cKDTree(xy).query_pairs(separation))
    for i, j in spatial_links:
        join(i, j)
    similar_links = []
    for i, row in enumerate(rows):
        a = np.asarray(row['shape_distances'])
        for j in range(i):
            b = np.asarray(rows[j]['shape_distances'])
            if row['mesh_sha256'] == rows[j]['mesh_sha256'] or (
                a.size and a.shape == b.shape and np.allclose(a, b, atol=.05, rtol=.005)
            ):
                join(i, j)
                similar_links.append([rows[j]['id'], row['id']])
    components = {}
    for i, row in enumerate(rows):
        components.setdefault(find(i), []).append(row['id'])
    groups = sorted(components.values())
    eligible = [g for g in groups if not set(g) & set(starter_ids)]
    ranked = sorted(eligible, key=lambda g: hashlib.sha256(
        ('point2building-holdout-v1:' + '|'.join(g)).encode()).hexdigest())
    take = math.ceil(len(ranked) * test_fraction)
    test_ids = {bid for group in ranked[:take] for bid in group}
    if not test_ids:
        raise ValueError('No starter-independent test group remains')
    assignment = {bid: 'test' if bid in test_ids else 'train' for g in groups for bid in g}
    group_id = {bid: 'group_' + hashlib.sha256('|'.join(g).encode()).hexdigest()[:16]
                for g in groups for bid in g}
    train_xy = xy[[assignment[r['id']] == 'train' for r in rows]]
    test_xy = xy[[assignment[r['id']] == 'test' for r in rows]]
    minimum = float(cKDTree(train_xy).query(test_xy)[0].min()) if len(train_xy) else None
    return {'assignment': assignment, 'group_ids': group_id, 'groups': groups,
            'eligible_group_count': len(eligible), 'test_group_count': take,
            'spatial_link_count': len(spatial_links), 'shape_similarity_links': similar_links,
            'minimum_train_test_center_distance_source_units': minimum,
            'policy': {'separation_source_units': separation,
                       'target_fraction_of_eligible_groups': test_fraction,
                       'shape_atol_source_units': .05, 'shape_rtol': .005,
                       'seed': 'point2building-holdout-v1',
                       'not_exhaustive_near_duplicate_detection': True}}
