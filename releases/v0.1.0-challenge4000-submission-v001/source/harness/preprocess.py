"""Input-only affine normalization, preserving observations and source coordinates."""
import numpy as np


def canonical_transform(points, target_diagonal=30.):
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 3 or not np.isfinite(p).all():
        raise ValueError('Expected at least three finite XYZ observations')
    low, high = p.min(0), p.max(0)
    diagonal = float(np.linalg.norm(high - low))
    if diagonal <= 1e-12 or not np.isfinite(target_diagonal) or target_diagonal <= 0:
        raise ValueError('Nondegenerate extent and positive finite target required')
    return (low + high) / 2, diagonal / target_diagonal


def normalize(points, origin, scale):
    return (np.asarray(points, dtype=np.float64) - origin) / scale


def restore(points, origin, scale):
    return np.asarray(points, dtype=np.float64) * scale + origin
