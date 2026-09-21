"""Read-only source audit; writes derived statistics beside this script."""
from pathlib import Path
import csv
import hashlib
import json
import time
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'work/audit'
OUT.mkdir(parents=True,exist_ok=True)

def main():
    started = time.time()
    summary = {}
    all_rows = []
    for split in ['xyz', 'LiDAR_xyz']:
        files = sorted((ROOT / 'data/inputs' / split).glob('*.xyz'), key=lambda p: int(p.stem))
        rows = []
        for i, path in enumerate(files):
            raw = path.read_bytes()
            row = dict(split=split, name=path.name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            try:
                p = np.loadtxt(raw.splitlines(), dtype=np.float64, ndmin=2)
                row.update(points=len(p), columns=p.shape[1], nonfinite=int((~np.isfinite(p)).sum()))
                if p.shape[1] == 3 and not row['nonfinite']:
                    mn, mx, mean = p.min(axis=0), p.max(axis=0), p.mean(axis=0)
                    for axis, j in zip('xyz', range(3)):
                        row.update({f'{axis}_min':float(mn[j]),f'{axis}_max':float(mx[j]),f'{axis}_span':float(mx[j]-mn[j]),f'{axis}_mean':float(mean[j]),f'{axis}_bbox_mid':float((mn[j]+mx[j])/2)})
                    zq = np.quantile(p[:,2], [.01,.05,.5,.95,.99])
                    row.update({f'z_q{k}':float(v) for k,v in zip(['01','05','50','95','99'],zq)})
                    row['xy_bbox_density'] = float(len(p)/max(np.prod(mx[:2]-mn[:2]),1e-12))
                else:
                    row['error'] = 'nonfinite or unexpected columns'
            except Exception as exc:
                row['error'] = str(exc)
            rows.append(row)
            if (i+1) % 500 == 0:
                print(f'{split}: {i+1}/{len(files)}; elapsed={time.time()-started:.1f}s', flush=True)
        valid = [r for r in rows if 'error' not in r]
        s = dict(files=len(rows),bytes=sum(r['bytes'] for r in rows),errors=[r for r in rows if 'error' in r],columns=sorted(set(r.get('columns',0) for r in rows)),points_total=sum(r['points'] for r in valid))
        for key in ['points','x_span','y_span','z_span','z_min','z_max','x_mean','y_mean','z_mean','x_bbox_mid','y_bbox_mid','z_bbox_mid','xy_bbox_density']:
            s[key] = dict(zip(['min','p05','median','p95','max'],map(float,np.quantile([r[key] for r in valid],[0,.05,.5,.95,1]))))
        s['smallest_by_points'] = [r['name'] for r in sorted(valid,key=lambda r:r['points'])[:5]]
        s['largest_by_points'] = [r['name'] for r in sorted(valid,key=lambda r:r['points'])[-5:]]
        s['exact_duplicate_files'] = len(rows)-len(set(r['sha256'] for r in rows))
        summary[split] = s
        all_rows.extend(rows)
    train = {r['sha256']:r['name'] for r in all_rows if r['split']=='xyz'}
    summary['exact_cross_split_duplicates'] = [(train[r['sha256']],r['name']) for r in all_rows if r['split']=='LiDAR_xyz' and r['sha256'] in train]
    summary['archives'] = {}
    for name in ['xyz.zip','LiDAR_xyz.zip']:
        with zipfile.ZipFile(ROOT/'data/archives'/name) as z:
            members = [i for i in z.infolist() if not i.is_dir()]
            exts = {}
            for info in members:
                ext = Path(info.filename).suffix
                exts[ext] = exts.get(ext,0)+1
            summary['archives'][name] = dict(files=len(members),extensions=exts,uncompressed_bytes=sum(i.file_size for i in members),first_names=[i.filename for i in members[:5]])
    keys = list(dict.fromkeys(k for r in all_rows for k in r))
    with (OUT/'pointcloud_inventory.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=keys)
        writer.writeheader()
        writer.writerows(all_rows)
    (OUT/'data_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(summary,indent=2,ensure_ascii=False),flush=True)

if __name__ == '__main__':
    main()
