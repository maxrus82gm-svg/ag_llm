"""Vendor a pinned private Windows runtime; no install, PATH or global config edits."""
from pathlib import Path
import hashlib
import importlib.metadata as md
import json
import shutil
import sys
import urllib.request
import zipfile
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

D=Path(__file__).resolve().parent
PLUGIN=D.parent/'plugin'
RUNTIME=PLUGIN/'runtime'
URL='https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip'
EXPECTED_MD5='fe8ef205f2e9c3ba44d0cf9954e1abd3'
assert sys.version_info[:3]==(3,12,10) and md.version('mcp')=='2.2.0'
assert not RUNTIME.exists(), 'Refuse to replace an existing runtime'
downloads=D/'downloads'; downloads.mkdir(exist_ok=True)
archive=downloads/'python-3.12.10-embed-amd64.zip'
if not archive.exists():
    with urllib.request.urlopen(URL, timeout=40) as response:
        body=response.read(15_000_000)
    assert len(body)<15_000_000
    archive.write_bytes(body)
body=archive.read_bytes()
assert hashlib.md5(body).hexdigest()==EXPECTED_MD5, 'Official release archive checksum mismatch'
RUNTIME.mkdir()
with zipfile.ZipFile(archive) as bundle:
    for member in bundle.infolist():
        target=(RUNTIME/member.filename).resolve()
        assert target.is_relative_to(RUNTIME.resolve())
    bundle.extractall(RUNTIME)
site=RUNTIME/'Lib/site-packages';site.mkdir(parents=True)
queue=[Requirement('mcp==2.2.0')]; selected={}; extras={}
while queue:
    req=queue.pop(0); name=canonicalize_name(req.name)
    dist=md.distribution(name)
    assert dist.version in req.specifier, f'Installed dependency does not satisfy {req}'
    added=set(req.extras)-extras.get(name,set())
    if name in selected and not added:continue
    selected[name]=dist;extras.setdefault(name,set()).update(req.extras)
    for item in dist.requires or []:
        dependency=Requirement(item)
        contexts=extras[name] or {''}
        if dependency.marker is None or any(dependency.marker.evaluate({'extra':extra}) for extra in contexts):
            queue.append(dependency)
records=[]
for name,dist in sorted(selected.items()):
    source_root=Path(dist.locate_file('')).resolve()
    copied=0;size=0;skipped=[]
    for item in dist.files or []:
        source=Path(dist.locate_file(item)).resolve()
        if not source.is_relative_to(source_root) or not source.is_file():
            skipped.append(str(item));continue
        if source.suffix=='.pyc' or '__pycache__' in source.parts:continue
        relative=source.relative_to(source_root)
        target=site/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert target.read_bytes()==source.read_bytes(), 'Dependency file collision'
        else:shutil.copyfile(source,target)
        copied+=1;size+=source.stat().st_size
    records.append({'name':name,'version':dist.version,'files':copied,'bytes':size,'skipped_outside_site_packages':skipped})
# Embedded _pth disables user-site/PYTHONPATH/registry discovery; package paths only.
(RUNTIME/'python312._pth').write_text('python312.zip\n.\nLib/site-packages\nimport site\n',encoding='ascii')
record={'python_version':'3.12.10','platform':'Windows x64','source_url':URL,
        'archive_md5_matches_official_release':True,'archive_sha256':hashlib.sha256(body).hexdigest(),
        'dependency_source':'Existing verified project venv distributions copied by installed metadata; no pip/global install',
        'distributions':records,'runtime_files':{},'no_system_path_dependency':True}
record['runtime_files']={p.relative_to(RUNTIME).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(RUNTIME.rglob('*')) if p.is_file()}
(D/'runtime_provenance.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'runtime_files':len(record['runtime_files']),'distributions':len(records),
                  'bytes':sum(p.stat().st_size for p in RUNTIME.rglob('*') if p.is_file())}))
