"""Explicit coordinates, strict OBJ parsing, immutable output helpers."""
from pathlib import Path
import hashlib
import json
import numpy as np
import mapbox_earcut


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)


def read_points(path, columns=(0, 1, 2)):
    if len(columns) != 3 or len(set(columns)) != 3 or min(columns) < 0:
        raise ValueError("Specify three distinct nonnegative XYZ column indices")
    p = np.loadtxt(path, usecols=columns, ndmin=2, dtype=np.float64)
    if len(p) < 3 or not np.isfinite(p).all():
        raise ValueError("Point cloud must contain >=3 finite XYZ points; invalid points are not silently discarded")
    return p


def read_obj(path):
    vertices, faces, lines, groups = [], [], [], []
    group = "unknown"
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        t = raw.split("#", 1)[0].split()
        if not t:
            continue
        if t[0] == "v":
            vertices.append([float(x) for x in t[1:4]])
        elif t[0] == "g":
            group = " ".join(t[1:]) or "unknown"
        elif t[0] in ("f", "l"):
            ids = []
            for x in t[1:]:
                n = int(x.split("/")[0])
                if n == 0:
                    raise ValueError("OBJ index zero is invalid")
                ids.append(n - 1 if n > 0 else len(vertices) + n)
            if t[0] == "f":
                if len(ids) < 3:
                    raise ValueError("OBJ face needs three vertices")
                faces.append(ids)
                groups.append(group)
            else:
                lines.extend(zip(ids[:-1], ids[1:]))
    v = np.asarray(vertices, dtype=float).reshape(-1, 3)
    if not len(v) or not np.isfinite(v).all():
        raise ValueError("Missing or nonfinite OBJ vertices")
    if any(i < 0 or i >= len(v) for row in [*faces, *lines] for i in row):
        raise ValueError("OBJ vertex index out of bounds")
    return {"vertices": v, "faces": faces, "lines": list(lines), "groups": groups}


def triangulate(obj):
    """Earcut in each polygon's local plane; preserve winding and face provenance."""
    v = obj["vertices"]
    triangles, source = [], []
    for fi, face in enumerate(obj["faces"]):
        q = v[face] - v[face].mean(axis=0)
        if len(face) == 3:
            ids = np.array([[0, 1, 2]])
        else:
            _, _, axes = np.linalg.svd(q, full_matrices=False)
            xy = np.ascontiguousarray(q @ axes[:2].T)
            ids = mapbox_earcut.triangulate_float64(xy, np.array([len(q)], dtype=np.uint32)).reshape(-1, 3)
            expected = np.cross(q, np.roll(q, -1, axis=0)).sum(axis=0)
            for tri in ids:
                a, b, c = q[tri]
                if np.dot(np.cross(b-a, c-a), expected) < 0:
                    tri[1], tri[2] = tri[2], tri[1]
        triangles.extend([[face[i] for i in row] for row in ids])
        source.extend([fi] * len(ids))
    if not triangles:
        raise ValueError("OBJ has no surface faces; a wireframe is not a mesh ground truth")
    return np.asarray(triangles, dtype=int), np.asarray(source, dtype=int)


def write_obj(path, vertices, faces, groups=None):
    with Path(path).open("x", encoding="utf-8") as f:
        f.write("# Source coordinates; no display transform\n")
        for p in vertices:
            f.write("v " + " ".join(f"{float(x):.12g}" for x in p) + "\n")
        for i, face in enumerate(faces):
            if groups:
                f.write("g " + groups[i] + "\n")
            f.write("f " + " ".join(str(int(x)+1) for x in face) + "\n")
