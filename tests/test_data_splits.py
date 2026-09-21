import numpy as np
import pytest
from scipy.spatial.distance import pdist
from harness.data_splits import grouped_holdout, author_holdout_without_starters
from harness.io import write_json
from harness.workflow import run_batch


def make_row(bid, x, lengths):
    return {'id': bid, 'center_xy': [x, 0], 'shape_distances': lengths, 'mesh_sha256': bid}


def test_spatial_chains_and_starter_near_duplicate_stay_out_of_test():
    # a-b-c is one connected component even though a-c exceeds the radius.
    rows = [make_row('a', 0, [1, 2, 3]), make_row('b', 150, [3, 4, 5]),
            make_row('c', 300, [5, 6, 7]), make_row('d', 2000, [1.01, 2.01, 3.01]),
            make_row('e', 3000, [10, 20, 30]), make_row('f', 4000, [50, 60, 70])]
    result = grouped_holdout(rows, {'a'})
    assert all(result['assignment'][bid] == 'train' for bid in ['a', 'b', 'c', 'd'])
    assert result['minimum_train_test_center_distance_source_units'] > 200
    assert result == grouped_holdout(list(reversed(rows)), {'a'})


def test_rigidly_transformed_reference_stays_in_starter_group():
    vertices = np.array([[0, 0, 0], [2, 0, 0], [0, 3, 0], [0, 0, 4]])
    transformed = vertices[:, [1, 0, 2]] * [-1, 1, 1] + [20, -40, 10]
    rows = [make_row('original', 0, np.sort(pdist(vertices))),
            make_row('rotated', 9000, np.sort(pdist(transformed))),
            make_row('unseen', 18000, [20, 30, 40])]
    result = grouped_holdout(rows, {'original'})
    assert result['assignment']['rotated'] == 'train'
    assert result['assignment']['unseen'] == 'test'


def test_synthetic_author_test_excludes_starters_and_similar_training_shapes():
    def row(bid, author_split, distances):
        return {'id': bid, 'author_split': author_split, 'shape_distances': distances,
                'mesh_sha256': bid, 'point_sha256': bid}
    rows = [row('train', 'trainset', [.1, .2, .3]),
            row('similar_test', 'testset', [.1000001, .2000001, .3000001]),
            row('starter_test', 'testset', [.4, .5, .6]),
            row('unseen_test', 'testset', [.7, .8, .9])]
    result = author_holdout_without_starters(rows, {'starter_test'})
    assert result['assignment'] == {'train': 'train', 'similar_test': 'train',
                                     'starter_test': 'train', 'unseen_test': 'test'}
    assert result == author_holdout_without_starters(list(reversed(rows)), {'starter_test'})
    assert result['policy']['spatial_isolation'].startswith('not_established')


@pytest.mark.parametrize('role, locked', [('sealed_test', False), ('deferred_train', False), ('development', True)])
def test_future_data_cannot_start_reconstruction(tmp_path, role, locked):
    manifest = tmp_path / 'manifest.json'
    write_json(manifest, {'role': role, 'stage_locked': locked, 'samples': []})
    output = tmp_path / 'must_not_exist'
    with pytest.raises(ValueError, match='sealed'):
        run_batch(tmp_path / 'does_not_exist.py', manifest, output)
    assert not output.exists()
