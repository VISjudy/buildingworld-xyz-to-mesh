"""Versioned LOCAL diagnostics. These metrics are not the official evaluator."""
from collections import defaultdict
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from .io import read_obj, read_points, triangulate, sha256

PROTOCOL = {
    "id": "local-geometry-v1", "official_equivalent": False,
    "distance": "Euclidean, unsquared, source coordinate units",
    "cd": "half the sum of two sampled nearest-neighbor mean distances",
    "ecd": "same reduction on length-uniform structure-edge samples",
    "normal": "bidirectional mean absolute dot at sampled nearest neighbors",
    "edge_angle_degrees": 10.0, "include_boundary_and_base_edges": True,
    "samples": 10000, "seed": 739,
    "coverage_tolerance": 0.15,
    "unit_status": "unverified; thresholds are provisional source-coordinate units",
}


def prepare(obj):
    t, source = triangulate(obj)
    # A common translation avoids catastrophic cancellation in georeferenced data.
    origin = obj["vertices"].mean(axis=0)
    mesh = trimesh.Trimesh(obj["vertices"] - origin, t, process=False)
    return mesh, source, origin


def structure_edges(obj, angle=10.0):
    v = obj["vertices"]
    incidence, normals = defaultdict(list), []
    for fi, face in enumerate(obj["faces"]):
        q = v[face] - v[face].mean(axis=0)
        n = np.cross(q, np.roll(q, -1, axis=0)).sum(axis=0)
        normals.append(n / max(np.linalg.norm(n), 1e-20))
        for a, b in zip(face, face[1:] + face[:1]):
            incidence[tuple(sorted((a, b)))].append(fi)
    edges = []
    for e, fs in incidence.items():
        if len(fs) != 2 or np.dot(normals[fs[0]], normals[fs[1]]) < np.cos(np.deg2rad(angle)):
            edges.append(e)
    return np.asarray(edges, dtype=int).reshape(-1, 2), incidence


def sample_lines(v, edges, n, seed):
    if not len(edges):
        return np.empty((0, 3))
    seg = v[np.asarray(edges)]
    lengths = np.linalg.norm(seg[:, 1] - seg[:, 0], axis=1)
    if lengths.sum() <= 0:
        return np.empty((0, 3))
    rng = np.random.default_rng(seed)
    ids = rng.choice(len(seg), size=n, p=lengths / lengths.sum())
    f = rng.random((n, 1))
    return seg[ids, 0] * (1 - f) + seg[ids, 1] * f


def stats(d, tolerance):
    return {"count": len(d), "mean": float(np.mean(d)), "median": float(np.median(d)),
            "p95": float(np.quantile(d, .95)), "max": float(np.max(d)),
            "coverage": float(np.mean(d <= tolerance)), "tolerance": tolerance,
            "exceed_count": int(np.sum(d > tolerance))}


def closest(mesh, points, batch=2048):
    # Bounded memory even for city-scale point files; evaluates every input point.
    distances, ids = [], []
    for start in range(0, len(points), batch):
        _, d, f = trimesh.proximity.closest_point(mesh, points[start:start+batch])
        distances.append(d)
        ids.append(f)
    return np.concatenate(distances), np.concatenate(ids)


def topology(obj, mesh, incidence):
    directions = defaultdict(list)
    for f in obj["faces"]:
        for a, b in zip(f, f[1:] + f[:1]):
            directions[tuple(sorted((a, b)))].append(1 if a < b else -1)
    open_edges = [list(e) for e, fs in incidence.items() if len(fs) == 1]
    nonmanifold = [list(e) for e, fs in incidence.items() if len(fs) > 2]
    winding = [list(e) for e, ds in directions.items() if len(ds) == 2 and sum(ds) != 0]
    degenerate = np.flatnonzero(mesh.area_faces <= 1e-12).tolist()
    return {"vertices": len(obj["vertices"]), "polygon_faces": len(obj["faces"]),
            "triangles": len(mesh.faces), "open_edges": open_edges,
            "nonmanifold_edges": nonmanifold, "inconsistent_winding_edges": winding,
            "degenerate_triangles": degenerate, "signed_volume": float(mesh.volume),
            "watertight": bool(mesh.is_watertight),
            "self_intersection": {"status": "not_checked", "count": None},
            "full_solid_validated": False}


def evaluate(mesh_path, points_path=None, gt_mesh=None, gt_wireframe=None, columns=(0, 1, 2), config=None):
    protocol = {**PROTOCOL, **(config or {})}
    if protocol["id"] != PROTOCOL["id"] or protocol["official_equivalent"]:
        raise ValueError("This evaluator cannot claim official equivalence")
    obj = read_obj(mesh_path)
    mesh, face_source, origin = prepare(obj)
    edges, incidence = structure_edges(obj, protocol["edge_angle_degrees"])
    report = {"protocol": protocol, "mesh_sha256": sha256(mesh_path),
              "topology": topology(obj, mesh, incidence),
              "official": {k: None for k in ["CD", "ECD", "NC", "V_Ratio", "F_Ratio", "Overall"]},
              "local_reference": None, "observed": None, "issues": []}
    for name in ["open_edges", "nonmanifold_edges", "inconsistent_winding_edges"]:
        if report["topology"][name]:
            report["issues"].append({"kind": name, "edge_vertex_ids": report["topology"][name], "rule_ids": ["K04"]})
    if points_path:
        p = read_points(points_path, columns)
        d, fi = closest(mesh, p - origin)
        report["input_sha256"] = sha256(points_path)
        worst = np.argsort(d)[-min(32, len(d)):][::-1]
        observed = {"all_points_to_surface": stats(d, protocol["coverage_tolerance"]),
                    "worst_points": [{"index": int(i), "xyz": p[i].tolist(), "distance": float(d[i]),
                                      "polygon_id": int(face_source[fi[i]])} for i in worst],
                    "per_nearest_polygon": []}
        for f in np.unique(face_source[fi]):
            mask = face_source[fi] == f
            observed["per_nearest_polygon"].append({"polygon_id": int(f), "group": obj["groups"][f],
                                                     **stats(d[mask], protocol["coverage_tolerance"])})
        # Normals are estimated only on stable local neighborhoods, with coverage disclosed.
        _, ix = cKDTree(p).query(p, k=min(16, len(p)))
        q = p[ix] - p[ix].mean(axis=1, keepdims=True)
        val, vec = np.linalg.eigh(np.einsum("nki,nkj->nij", q, q))
        stable = (val[:, 0] / np.maximum(val.sum(1), 1e-20) < .03) & (val[:, 1] > 1e-12)
        dots = np.abs(np.einsum("ij,ij->i", vec[:, :, 0], mesh.face_normals[fi]))
        observed["estimated_normal_alignment"] = {"status": "input_proxy_not_gt_NC", "stable_points": int(stable.sum()),
            "fraction": float(stable.mean()), "mean_abs_dot": float(dots[stable].mean()) if stable.any() else None}
        observed["reverse_distance"] = {"status": "not_scored_without_visibility", "reason": "Missing returns do not establish empty space"}
        report["observed"] = observed
        if observed["all_points_to_surface"]["p95"] > protocol["coverage_tolerance"]:
            report["issues"].append({"kind": "observed_surface_mismatch", "locations": observed["worst_points"], "rule_ids": ["K01", "K02", "K03", "K06"]})
    if gt_mesh:
        gt = read_obj(gt_mesh)
        gm, _, go = prepare(gt)
        ps, pi = trimesh.sample.sample_surface(mesh, protocol["samples"], seed=protocol["seed"])
        gs, gi = trimesh.sample.sample_surface(gm, protocol["samples"], seed=protocol["seed"])
        gs += go - origin
        dp, ip = cKDTree(gs).query(ps)
        dg, ig = cKDTree(ps).query(gs)
        nc = .5 * (np.abs((mesh.face_normals[pi] * gm.face_normals[gi[ip]]).sum(1)).mean()
                   + np.abs((gm.face_normals[gi] * mesh.face_normals[pi[ig]]).sum(1)).mean())
        report["local_reference"] = {"CD": float(.5*(dp.mean()+dg.mean())), "NC": float(nc),
            "V_Ratio": len(obj["vertices"])/len(gt["vertices"]), "F_Ratio": len(obj["faces"])/len(gt["faces"]),
            "ECD": None, "gt_mesh_sha256": sha256(gt_mesh), "not_official": True}
        if not gt_wireframe:
            ge, _ = structure_edges(gt, protocol["edge_angle_degrees"])
            gt_wire = (gt["vertices"] - origin, ge)
    if gt_wireframe or gt_mesh:
        if gt_wireframe:
            wf = read_obj(gt_wireframe)
            if not wf["lines"]:
                raise ValueError("Ground truth wireframe must contain OBJ line elements")
            gt_wire = (wf["vertices"] - origin, wf["lines"])
        pe = sample_lines(obj["vertices"] - origin, edges, protocol["samples"], protocol["seed"])
        ge = sample_lines(*gt_wire, protocol["samples"], protocol["seed"])
        ecd = float(.5*(cKDTree(ge).query(pe)[0].mean()+cKDTree(pe).query(ge)[0].mean())) if len(pe) and len(ge) else None
        if report["local_reference"] is None:
            report["local_reference"] = {"CD": None, "NC": None, "V_Ratio": None, "F_Ratio": None, "not_official": True}
        report["local_reference"]["ECD"] = ecd
        if gt_wireframe:
            report["local_reference"]["gt_wireframe_sha256"] = sha256(gt_wireframe)
    return report
