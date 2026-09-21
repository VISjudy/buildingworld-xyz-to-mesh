import numpy as np
import pytest
from harness.preprocess import canonical_transform, normalize, restore


def test_input_only_transform_is_scale_translation_equivariant_and_reversible():
    points = np.array([[0., 0, 2], [5, 0, 4], [0, 3, 8], [5, 3, 6]])
    o, s = canonical_transform(points)
    local = normalize(points, o, s)
    assert np.linalg.norm(np.ptp(local, axis=0)) == pytest.approx(30)
    moved = points * .07 + [2678000, 1250000, 300]
    o2, s2 = canonical_transform(moved)
    np.testing.assert_allclose(normalize(moved, o2, s2), local, atol=1e-7)
    # Reference extends beyond observed points: it must use input transform, not its own bbox.
    gt = points * 2
    np.testing.assert_allclose(restore(normalize(gt, o, s), o, s), gt, atol=1e-12)
    assert np.linalg.norm(np.ptp(normalize(gt, o, s), axis=0)) == pytest.approx(60)


def test_nonfinite_points_are_rejected_not_removed():
    with pytest.raises(ValueError):
        canonical_transform([[0, 0, 0], [1, 2, 3], [np.nan, 2, 3]])
