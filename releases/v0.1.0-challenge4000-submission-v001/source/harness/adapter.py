"""Run the unchanged historical baseline in a fresh subprocess via this adapter."""
import argparse
import contextlib
import importlib.util
from pathlib import Path
import os
import shutil
import numpy as np
from .io import read_points, write_json, sha256, read_obj


def reconstruct(source, points, output, columns=(0, 1, 2), localize=False):
    source, points, output = Path(source).resolve(), Path(points).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    p = read_points(points, columns)
    if len(p) < 24 or np.ptp(p[:, :2], axis=0).min() <= 1e-10:
        raise ValueError("Historical baseline requires >=24 points and nondegenerate XY")
    origin = (p.min(axis=0)+p.max(axis=0))/2 if localize else np.zeros(3)
    staged = output / "staged" / "LiDAR_xyz"
    staged.mkdir(parents=True)
    # For exact historical three-column reproduction, retain original bytes.
    if columns == (0, 1, 2) and not localize and np.loadtxt(points, max_rows=1, ndmin=2).shape[1] == 3:
        shutil.copyfile(points, staged / "input.xyz")
    else:
        np.savetxt(staged / "input.xyz", p-origin, fmt="%.17g")
    os.environ["MPLCONFIGDIR"] = str(output / "mplconfig")
    spec = importlib.util.spec_from_file_location("frozen_reconstructor", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = staged.parent
    module.OUT = output / "models"
    module.OUT.mkdir()
    with (output / "execution.txt").open("x", encoding="utf-8") as log, contextlib.redirect_stdout(log):
        data, _, _ = module.run("input")
    raw = module.OUT / "input_lod2.obj"
    mesh_path = output / "model.obj"
    if localize:
        from .io import write_obj
        obj = read_obj(raw)
        write_obj(mesh_path, obj["vertices"]+origin, obj["faces"], obj["groups"])
    else:
        shutil.copyfile(raw, mesh_path)
    parsed = read_obj(mesh_path)
    write_json(output / "adapter.json", {"source_sha256": sha256(source), "input_sha256": sha256(points),
        "columns": list(columns), "origin": origin.tolist(), "output_sha256": sha256(mesh_path),
        "roundtrip_vertices": len(parsed["vertices"]), "roundtrip_faces": len(parsed["faces"]),
        "adapter_does_not_modify_source": True, "localize": localize})
    return mesh_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--points", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--columns", nargs=3, type=int, default=[0, 1, 2])
    ap.add_argument("--localize", action="store_true")
    args = ap.parse_args()
    reconstruct(args.source, args.points, args.output, tuple(args.columns), args.localize)
