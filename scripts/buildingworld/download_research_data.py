"""Download public research archives without executing upstream code or replacing files."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.request


def download(url,destination,expected_bytes,source_page):
    dest=Path(destination).resolve();dest.parent.mkdir(parents=True,exist_ok=True)
    part=dest.with_name(dest.name+'.part')
    if dest.exists() or part.exists():raise FileExistsError('Choose a new destination; existing download is preserved')
    if not url.startswith('https://'):raise ValueError('HTTPS required')
    digest=hashlib.sha256();count=0;start=time.monotonic();last=start
    with urllib.request.urlopen(url,timeout=90) as response:
        if response.status!=200:raise ValueError('Unexpected HTTP response')
        if 'text/html' in response.headers.get('Content-Type',''):raise ValueError('Received HTML, not data')
        announced=response.headers.get('Content-Length')
        if announced and int(announced)!=expected_bytes:raise ValueError('Unexpected archive size')
        with part.open('xb') as f:
            while block:=response.read(1024*1024):
                count+=len(block)
                if count>expected_bytes:raise ValueError('Download exceeds expected size')
                f.write(block);digest.update(block)
                if time.monotonic()-last>15:
                    print(f'{dest.name}: {count/1e6:.1f}/{expected_bytes/1e6:.1f} MB',flush=True);last=time.monotonic()
    if count!=expected_bytes:raise ValueError('Incomplete download retained as .part')
    part.rename(dest)
    record={'source_page':source_page,'download_url':url,'filename':dest.name,'bytes':count,'sha256':digest.hexdigest(),
            'hash_status':'locally_computed_not_publisher_checksum','downloaded_utc':datetime.now(timezone.utc).isoformat(),
            'seconds':time.monotonic()-start}
    with dest.with_name(dest.name+'.provenance.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
    print(json.dumps(record),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--destination',required=True)
    p.add_argument('--expected-bytes',required=True,type=int);p.add_argument('--source-page',required=True)
    download(**vars(p.parse_args()))
