"""Recheck cached release ZIP and installed bytes, without executing or extracting EXEs."""
from pathlib import Path
import json
import hashlib
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
OLD=ROOT/'reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001'
BASE=OLD/'secure_tunnel_preparation'

def digest(b):return hashlib.sha256(b).hexdigest()
def main():
    metadata=json.loads((BASE/'official_release_metadata.json').read_text(encoding='utf-8-sig'))
    name='tunnel-client-v0.0.16-windows-amd64.zip'
    asset=next(x for x in metadata['assets'] if x['name']==name)
    archive=BASE/'downloads'/name
    zsha=digest(archive.read_bytes())
    sumline=next(s for s in (BASE/'downloads/SHA256SUMS.txt').read_text().splitlines() if s.strip().endswith(name))
    installed=(BASE/'tools/tunnel-client.exe').read_bytes()
    with zipfile.ZipFile(archive) as z:
        entries=[x for x in z.infolist() if Path(x.filename).name=='tunnel-client.exe']
        assert len(entries)==1
        assert entries[0].file_size<32*1024*1024
        packaged=z.read(entries[0])
    paths=json.loads((OLD/'native_client_offline_20261017/binary_symbols.json').read_text())['project_file_paths']
    selected=[x for x in paths if any(s in x.lower() for s in ['runtimeconfig','transport','controlplane','mcpclient','harpoon','oauth','cloudflared','proxyhealth'])]
    result={
        'cached_metadata_tag':metadata['tag_name'],'metadata_revalidated_online':False,
        'archive':{'path':str(archive),'bytes':archive.stat().st_size,'sha256':zsha,
                   'matches_cached_release_digest':asset.get('digest')=='sha256:'+zsha,
                   'matches_cached_SHA256SUMS':sumline.split()[0]==zsha},
        'installed_exe':{'bytes':len(installed),'sha256':digest(installed),
                         'identical_to_zip_member':installed==packaged,
                         'expected_sha256_match':digest(installed)=='4226bb74a72388147882881f29f79801b95e285d731a138071812e3aa6766571',
                         'commit_literal_offset':installed.find(b'5f99daabd4aa4a77049e6d81d54a0d8c18335397'),
                         'executed':False},
        'cached_cli_version':(BASE/'version.txt').read_text(encoding='utf-8-sig').strip(),
        'source_binary_reproducible_build_proven':False,
        'full_runtime_source_available':False,
        'binary_source_path_hints_not_source_text':selected,
        'limitation':'Cached release metadata and ZIP identity are origin clues, not independent upstream attestation or a reproducible build.'}
    with (OUT/'provenance.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='binary_source_path_hints_not_source_text'},ensure_ascii=False,indent=2))
    print('SELECTED_PATH_HINTS',len(selected))

if __name__=='__main__':main()
