"""Check staged byte preservation of the new immutable release artifacts."""
import hashlib,json,subprocess,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[3]
work=root/'work/experiments/2026-09-21/feedback-components-v002'
versions=['v0.1.3-text-no-k-v002','v0.1.3-text-k-v002','v0.1.3-full-feedback-v002','v0.1.3-height-guard-off-v002','v0.5.1-starter78-comparison-v002','v0.1.3-text-no-k-raw-v002']
expected={}
for v in versions:
    d=root/'releases'/v
    manifest=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
    for name,digest in manifest['files'].items():
        assert hashlib.file_digest((d/name).open('rb'),'sha256').hexdigest()==digest,str(d/name)
        expected[f'releases/{v}/{name}']=digest
tree=subprocess.check_output(['git','write-tree'],cwd=root,text=True).strip()
archive=work/'staged-releases-snapshot.tar'
assert not archive.exists()
subprocess.run(['git','archive','--format=tar','--output',str(archive),tree,*[f'releases/{v}'for v in versions]],cwd=root,check=True)
found=set()
with tarfile.open(archive)as tar:
    for member in tar:
        if member.name in expected:
            assert hashlib.file_digest(tar.extractfile(member),'sha256').hexdigest()==expected[member.name],member.name
            found.add(member.name)
assert found==set(expected),'Missing frozen files'
result={'staged_tree':tree,'versions':versions,'frozen_files_checked':len(found),'all_worktree_and_staged_hashes_match':True,'scope':'Frozen source/models/knowledge/renders/results; proof and administrative files are not self-hashed.'}
with(root/'reports/2026-09-21-feedback-components-v002/git-snapshot-verification.json').open('x',encoding='utf-8')as f:json.dump(result,f,indent=2)
print(json.dumps(result))
