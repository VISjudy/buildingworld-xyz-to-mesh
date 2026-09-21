"""Read-only starter78 height audit; GT is used for diagnosis, never inference.

Outputs are exclusive-created. PCA filters and 2%/5% height bands are descriptive
audit settings, not selected deployment thresholds. No reconstruction is run.
"""
from pathlib import Path
import csv
import json
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from harness.io import read_json, read_obj, read_points, sha256, write_json
from harness.preprocess import canonical_transform, normalize, restore

MANIFEST = ROOT / "work/experiments/2026-09-21/starter78-feedback-pilot/setup/all78.json"
OUTPUT = ROOT / "work/experiments/2026-09-21/feedback-components-v002/height-audit"
QUANTILES = {"min": 0, "q001": .001, "q01": .01, "q99": .99, "q999": .999, "max": 1}


def describe(values):
    a = np.array([v for v in values if v is not None], dtype=float)
    return dict(n=len(a), min=float(a.min()), median=float(np.median(a)),
                mean=float(a.mean()), p95=float(np.quantile(a, .95)), max=float(a.max())) if len(a) else {"n": 0}


def roof_support(points):
    """Only input geometry: local PCA, upper half, roof-compatible normal.

    This is a heuristic subset, NOT a verified semantic roof label. Thresholds
    are fixed before GT comparisons and are not fitted on the audit outcomes.
    """
    k = min(16, len(points))
    _, neighbors = cKDTree(points).query(points, k=k, workers=1)
    local = points[neighbors]
    local -= local.mean(axis=1, keepdims=True)
    covariance = np.einsum("nki,nkj->nij", local, local) / k
    ev, vec = np.linalg.eigh(covariance)
    planarity = (ev[:, 1] - ev[:, 0]) / np.maximum(ev[:, 2], 1e-15)
    curvature = ev[:, 0] / np.maximum(ev.sum(axis=1), 1e-15)
    return ((planarity >= .5) & (curvature <= .05) &
            (np.abs(vec[:, 2, 0]) >= .5) &
            (points[:, 2] >= np.median(points[:, 2])))


def audit(sample):
    p = read_points(sample["points"])
    v = read_obj(sample["gt_mesh"])["vertices"]
    tr = read_json(sample["transform"])
    assert tr["gt_used_to_define_transform"] is False
    assert sha256(sample["points"]) == sample["point_sha256"]
    assert sha256(sample["gt_mesh"]) == sample["mesh_sha256"]
    o, s = np.array(tr["origin"]), float(tr["scale"])
    source_p = restore(p, o, s)
    source_v = restore(v, o, s)
    original_p = read_points(tr["source_points"])
    original_v = read_obj(tr["source_mesh"])["vertices"]
    bottom, top = float(v[:, 2].min()), float(v[:, 2].max())
    height = top - bottom
    assert height > 0
    r = {"id": sample["id"], "stratum": sample["evaluation_stratum"],
         "point_count": len(p), "source_coordinate_frame": tr["source_coordinate_frame"],
         "canonical_origin_source_z": float(o[2]), "source_units_per_canonical_unit": s,
         "gt_min_canonical": bottom, "gt_max_canonical": top, "gt_height_canonical": height,
         "gt_min_source": float(source_v[:, 2].min()), "gt_max_source": float(source_v[:, 2].max()),
         "gt_height_source": height * s,
         "source_point_restore_max_abs_error": float(np.max(np.abs(source_p - original_p))),
         "source_mesh_restore_max_abs_error": float(np.max(np.abs(source_v - original_v))),
         "canonical_zero_is_ground": False,
         "negative_canonical_point_fraction": float(np.mean(p[:, 2] < 0)),
         "negative_source_point_fraction": float(np.mean(source_p[:, 2] < 0))}
    for label, q in QUANTILES.items():
        value = float(np.quantile(p[:, 2], q))
        r[f"point_{label}_canonical"] = value
        r[f"point_{label}_source"] = value * s + o[2]
        for target, z in (("base", bottom), ("roof", top)):
            error = value - z
            r[f"{label}_{target}_signed_error_canonical"] = error
            r[f"{label}_{target}_signed_error_source"] = error * s
            r[f"{label}_{target}_signed_error_over_gt_height"] = error / height
            r[f"{label}_{target}_abs_error_over_gt_height"] = abs(error) / height
    r["point_range_over_gt_height"] = float(np.ptp(p[:, 2]) / height)
    r["point_01_99_range_over_gt_height"] = float((np.quantile(p[:, 2], .99) - np.quantile(p[:, 2], .01)) / height)
    r["points_below_gt_base_2pct_fraction"] = float(np.mean(p[:, 2] < bottom - .02 * height))
    r["points_above_gt_roof_2pct_fraction"] = float(np.mean(p[:, 2] > top + .02 * height))
    r["gt_base_below_input_min_2pct"] = bool(p[:, 2].min() > bottom + .02 * height)
    r["input_min_below_gt_base_2pct"] = bool(p[:, 2].min() < bottom - .02 * height)
    supported = roof_support(p)
    r["pca_roof_candidate_count"] = int(supported.sum())
    r["pca_roof_candidate_fraction"] = float(supported.mean())
    for label, q in (("max", 1), ("q99", .99)):
        z = float(np.quantile(p[supported, 2], q)) if supported.any() else None
        r[f"pca_roof_{label}_canonical"] = z
        r[f"pca_roof_{label}_source"] = z * s + o[2] if z is not None else None
        r[f"pca_roof_{label}_abs_error_over_gt_height"] = abs(z - top) / height if z is not None else None
    # A synthetic global translation is a numerical check of preprocessing,
    # not a new sample or reconstruction experiment.
    shift = np.array([127.5, -233.25, 1000.0])
    o0, s0 = canonical_transform(source_p)
    o1, s1 = canonical_transform(source_p + shift)
    c0, c1 = normalize(source_p, o0, s0), normalize(source_p + shift, o1, s1)
    r["translation_canonical_max_abs_error"] = float(np.max(np.abs(c0 - c1)))
    r["translation_scale_abs_error"] = abs(s1 - s0)
    r["translation_origin_max_abs_error"] = float(np.max(np.abs(o1 - o0 - shift)))
    r["translation_restored_gt_max_abs_error"] = float(np.max(np.abs(restore(v, o1, s1) - restore(v, o0, s0) - shift)))
    return r


def group_summary(rows):
    data = {"n": len(rows), "source_coordinate_frames": sorted({r["source_coordinate_frame"] for r in rows})}
    for field in ("gt_height_canonical", "gt_height_source", "gt_min_source", "gt_max_source",
                  "canonical_origin_source_z", "point_range_over_gt_height", "point_01_99_range_over_gt_height",
                  "negative_canonical_point_fraction", "negative_source_point_fraction",
                  "points_below_gt_base_2pct_fraction", "points_above_gt_roof_2pct_fraction", "pca_roof_candidate_fraction"):
        data[field] = describe([r[field] for r in rows])
    data["base_above_lowest_return_count_2pct"] = sum(r["input_min_below_gt_base_2pct"] for r in rows)
    data["base_below_lowest_return_count_2pct"] = sum(r["gt_base_below_input_min_2pct"] for r in rows)
    data["comparisons"] = {}
    for label in QUANTILES:
        for target in ("base", "roof"):
            metric = f"{label}_{target}_abs_error_over_gt_height"
            signed = f"{label}_{target}_signed_error_over_gt_height"
            a = [r[metric] for r in rows]
            data["comparisons"][f"{label}_vs_{target}"] = {
                "abs_error_over_gt_height": describe(a),
                "signed_error_over_gt_height": describe([r[signed] for r in rows]),
                "signed_error_canonical": describe([r[f"{label}_{target}_signed_error_canonical"] for r in rows]),
                "within_2pct_count": sum(x <= .02 for x in a), "within_5pct_count": sum(x <= .05 for x in a),
                "worst_three": [{"id": r["id"], "signed_error_over_gt_height": r[signed],
                                  "point_source_z": r[f"point_{label}_source"],
                                  "gt_source_z": r["gt_min_source" if target == "base" else "gt_max_source"]}
                                 for r in sorted(rows, key=lambda r: r[metric], reverse=True)[:3]]}
    for label in ("max", "q99"):
        a = [r[f"pca_roof_{label}_abs_error_over_gt_height"] for r in rows]
        data["comparisons"][f"pca_roof_{label}_vs_roof"] = {
            "abs_error_over_gt_height": describe(a),
            "within_2pct_count": sum(x is not None and x <= .02 for x in a),
            "within_5pct_count": sum(x is not None and x <= .05 for x in a),
            "missing_support_count": sum(x is None for x in a)}
    return data


def findings(summary):
    lines = ["# starter78 点云 Z / 参考 Mesh 高度审计", "",
             "只读固定 78 对开发集：真实 Zurich 38，仿真 mini 40。没有重建或对完整432/封存130评分。所有误差相对于作者参考 Mesh，不保证物理真值。", "",
             "反馈边界：本文全78统计供用户审阅，不能整体送入候选提议agent。summary.json另含旧固定discovery24/selection24/transfer30分区；本轮新增知识只允许引用discovery24观测。selection/transfer高度审核不得回流本轮候选。下文K09属于坐标/可观测性假设，未经部署验证。", "",
             "## 坐标语义", "",
             "点云 Z 是坐标，不自动等于离地高度。canonical 坐标满足 z_c=(z_source-o_z)/s；z_c=0 只表示输入包围盒中高。Zurich 可恢复作者源坐标，但 CRS/高程基准未独立核准，源单位不可擅称米。mini 缺源世界坐标变换，只能恢复作者归一化坐标。每栋 o_z、源底高/屋顶标高、缩放与极值见 per_building.csv。", "",
             "建筑高度是屋顶与可信地面/基底之间的差，且一般可以随 XY 变化。Mesh 的最小 Z 是参考模型的底高，未保证等于实际可见地面。", "",
             "## 描述统计", "",
             "下表 2%/5% 为本次描述性审核误差带，不是从 GT 学得或可部署的异常阈值。各项逐栋归一化分母为 GT 总高；canon 为分析单位。原始极值保留全部输入；PCA 子集不删除原数据或替代完整观测评分。", "",
             "| 来源 | 数量 | 高度估计/端点 | 绝对误差中位数 / GT高度 | P95 / GT高度 | ≤2%栋数 | ≤5%栋数 |",
             "|---|---:|---|---:|---:|---:|---:|"]
    for name, group in summary["by_stratum"].items():
        for metric in ("min_vs_base", "q001_vs_base", "q01_vs_base", "max_vs_roof", "q999_vs_roof", "q99_vs_roof", "pca_roof_max_vs_roof", "pca_roof_q99_vs_roof"):
            m = group["comparisons"][metric]
            a = m["abs_error_over_gt_height"]
            lines.append(f"| {name} | {group['n']} | {metric} | {a['median']:.4f} | {a['p95']:.4f} | {m['within_2pct_count']} | {m['within_5pct_count']} |")
        lines.extend(["", f"{name}：GT canonical高度中位数 {group['gt_height_canonical']['median']:.6f}；输入Z全跨度/GT高度中位数 {group['point_range_over_gt_height']['median']:.6f}。最低回波高于参考底面超过2%高度：{group['base_below_lowest_return_count_2pct']}/{group['n']}；最低回波低于参考底面超过2%高度：{group['base_above_lowest_return_count_2pct']}/{group['n']}。", ""])
    lines += ["## 反例", "", "以下按最坏误差选出用于诊断，不能当无偏性能样本。源坐标单位依来源而异。", ""]
    for name, group in summary["by_stratum"].items():
        for metric in ("min_vs_base", "max_vs_roof"):
            for r in group["comparisons"][metric]["worst_three"]:
                lines.append(f"- {name} / {metric} / `{r['id']}`：输入端点 Z={r['point_source_z']:.8f}，参考端点 Z={r['gt_source_z']:.8f}；有符号误差/GT高度={r['signed_error_over_gt_height']:.6f}。")
    lines += ["", "## 输入 PCA 屋面支持的限定", "",
              "对输入 k=16 近邻做局部 PCA；planarity≥0.5、最小特征值占比≤0.05、|normal_z|≥0.5 且 z≥输入中位数，作为屋面候选。参数先于比较固定，仅用于本次几何诊断；没有 GT 参与点选择，也没有逐点语义真值。局部树冠、设备、过渡面可误入；尖顶/小面可漏检。候选最大Z/q99不能证明真实最高屋脊标高。不能由此直接得到建筑全高。", "",
              "## K09 建议：坐标不变的高度支持检查 [待验证假设]", "",
              "1. 保留输入变换及坐标系。候选屋面与输入支持必须在同一坐标系比较：使用差值 r=z_pred(x,y)-z_support(x,y)，再除以输入估计的稳健尺度或噪声尺度。不能用 z<0、z=0 或源坐标绝对数值判断异常。",
              "2. 可信屋面局部面片须有独立于GT的点数、空间覆盖、平面残差和法向支持；允许同一建筑多层屋面。审计中的GT最大Z只能评估端点，不能在推理时提供屋面高度或阈值。",
              "3. 基底需要地面分类、DTM、可信周边地面或明确的建模先验。最低回波只提供观测下界线索，不能自动标为地面；缺底部观测时记为 ground_unobserved/base_assumed，保留默认算法的补全假设与不确定性。",
              "4. 用户提出异常Z回退默认算法，可定义为：新规则缺乏输入支持、局部高度残差超出预先校准的输入噪声容差、或结构约束失败，则回退冻结默认算法并记录原因。不能用GT判定回退。默认算法自身也须通过坐标一致性、拓扑和观测诊断；回退不等于结果正确。",
              "5. 部署阈值尚未学习或独立校准。本次≤2%GT高度仅作事后描述，推理无法访问GT高度，不能直接照搬。噪声尺度及支持阈值应在discovery预设、selection验证，并保留失败及退化。", "",
              "## 平移等变性", "",
              "令 p'=p+t。由输入bbox定义的 o'=o+t 且 s'=s，因此 (p'-o')/s'=(p-o)/s，canonical输入保持不变。若规则只用canonical几何，预测canonical不变，恢复后 M'=s M_c+o+t=M+t；高度差、法向、局部残差及其尺度比保持不变。直接使用源Z正负的判据不满足此性质：整体加1000即可改变分支。", "",
              f"逐栋以 t=(127.5,-233.25,1000) 数值验证预处理：最大canonical差 {summary['verification']['translation_canonical_max_abs_error']:.3e}，恢复参考几何平移偏差 {summary['verification']['translation_restored_gt_max_abs_error']:.3e}。这证明/检查坐标变换，不声称实际默认重建算法已经通过平移测试。", "",
              "## 结论与限制", "",
              "屋顶标高是否匹配取决于输入覆盖、极值噪声及参考几何差异，不能普遍保证；全跨度也不等于建筑全高。最低回波不普遍等于模型底面，更不能据此确认物理地面。平移坐标不会修复缺失的地面信息。", "",
              "本数据经过闭合/立面质量筛选，且全部是开发样例，存在筛选偏差。仅以端点审核没有评估逐面屋顶匹配、坡屋面局部标高、XY轮廓或完整重建质量；没有训练/验证部署阈值。"]
    return "\n".join(lines) + "\n"


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"Preserve existing audit: {OUTPUT}")
    samples = read_json(MANIFEST)["samples"]
    assert len(samples) == 78 and len({s["id"] for s in samples}) == 78
    assert sum(s["evaluation_stratum"] == "real_zurich" for s in samples) == 38
    assert sum(s["evaluation_stratum"] == "synthetic_mini" for s in samples) == 40
    partition_ids = {name: {s["id"] for s in read_json(MANIFEST.parent / f"{name}.json")["samples"]}
                     for name in ("discovery", "selection", "transfer")}
    assert [len(partition_ids[x]) for x in partition_ids] == [24, 24, 30]
    assert len(set.union(*partition_ids.values())) == 78
    rows = [audit(s) for s in samples]
    for row in rows:
        row["partition"] = next(name for name, ids in partition_ids.items() if row["id"] in ids)
    keys = ("source_point_restore_max_abs_error", "source_mesh_restore_max_abs_error",
            "translation_canonical_max_abs_error", "translation_scale_abs_error",
            "translation_origin_max_abs_error", "translation_restored_gt_max_abs_error")
    summary = {"status": "descriptive_audit_completed_not_reconstruction_or_deployment_validation",
               "manifest": str(MANIFEST), "manifest_sha256": sha256(MANIFEST),
               "script_sha256": sha256(__file__), "count": len(rows),
               "scope": "fixed starter78 only; no full432 or sealed130 reconstruction/scoring",
               "gt_usage": "descriptive endpoint comparison only; absent from PCA selection and inference rule",
               "threshold_status": "2pct/5pct GT height descriptive audit bands; not learned deployment thresholds",
               "quantiles": QUANTILES,
               "pca_settings": {"k": 16, "planarity_min": .5, "curvature_max": .05, "abs_nz_min": .5, "z_filter": "above_input_median", "semantic_roof_labels": False},
               "by_stratum": {name: group_summary([r for r in rows if r["stratum"] == name])
                              for name in ("real_zurich", "synthetic_mini")},
               "candidate_feedback_boundary": "Only by_partition.discovery may enter current candidate proposals; all78/selection/transfer audit is user-facing analysis, not proposal feedback.",
               "by_partition": {partition: {"n": len(ids), "by_stratum": {
                   name: group_summary([r for r in rows if r["id"] in ids and r["stratum"] == name])
                   for name in ("real_zurich", "synthetic_mini")}}
                   for partition, ids in partition_ids.items()},
               "verification": {key: max(r[key] for r in rows) for key in keys}}
    assert summary["verification"]["source_point_restore_max_abs_error"] <= 1e-8
    assert summary["verification"]["source_mesh_restore_max_abs_error"] <= 1e-5
    assert summary["verification"]["translation_canonical_max_abs_error"] <= 1e-7
    OUTPUT.mkdir(parents=True, exist_ok=False)
    write_json(OUTPUT / "summary.json", summary)
    with (OUTPUT / "per_building.csv").open("x", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (OUTPUT / "findings.md").open("x", encoding="utf-8") as f:
        f.write(findings(summary))
    print(json.dumps({"output": str(OUTPUT), "count": len(rows), "verification": summary["verification"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
