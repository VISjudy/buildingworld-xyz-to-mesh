"""Verify staged Git bytes against immutable release manifests before commit."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
root=Path(__file__).resolve().parents[3]
work=root/'work/experiments/2026-09-21/starter78-feedback-pilot'
tree=subprocess.check_output(['git','write-tree'],cwd=root,text=True).strip()
archive=work/'staged-snapshot.tar'
assert not archive.exists()
subprocess.run(['git','archive','--format=tar','--output',str(archive),tree],cwd=root,check=True)
versions=['v0.1.0-starter78-standard-v001','v0.1.2-pilot-f0-v001','v0.1.2-pilot-f3-v001','v0.1.2-transfer-original-v001','v0.1.2-transfer-evolved-v001']
expected={}
for version in versions:
    manifest=json.loads((root/'releases'/version/'manifest.json').read_text(encoding='utf-8'))
    expected.update({f'releases/{version}/{name}':digest for name,digest in manifest['files'].items()})
found=set()
with tarfile.open(archive) as tar:
    for member in tar:
        if member.name in expected:
            digest=hashlib.file_digest(tar.extractfile(member),'sha256').hexdigest()
            assert digest==expected[member.name],member.name
            found.add(member.name)
assert found==set(expected), 'Missing frozen files in Git tree'
report={'staged_tree':tree,'frozen_files_checked':len(found),'all_hashes_match':True,
        'scope':'Frozen source/models/knowledge/renders/results; proof and later administrative files are not self-hashed.'}
path=root/'reports/2026-09-21-starter78-feedback-pilot/git-snapshot-verification.json'
with path.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
