"""Offline byte inspection. Never executes tunnel-client or opens a socket.

Only writes JSON/TXT beside this source. No downloads, Git, subprocesses or
configuration changes. Symbols and embedded docs are NOT recovered source code.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zipfile

OUT = Path(__file__).resolve().parent
TASK = OUT.parent
PREP = TASK / "secure_tunnel_preparation"
EXE = PREP / "tools/tunnel-client.exe"
EXPECTED_SHA = "4226bb74a72388147882881f29f79801b95e285d731a138071812e3aa6766571"
PREFIX = "github.com/openai/tunnel-client/"


def guard(event, args):
    if event.startswith(("socket.", "subprocess.", "ctypes.")) or event in {
        "os.system", "os.spawn", "os.posix_spawn", "os.exec"
    }:
        raise RuntimeError("STATIC_AUDIT_FORBIDDEN_OPERATION:" + event)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save(name: str, data):
    target = OUT / name
    if target.parent != OUT or target.suffix not in {".json", ".txt"}:
        raise ValueError("output outside audit directory")
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    target.write_text(text, encoding="utf-8")


def uvarint(data: bytes, pos: int):
    value = 0
    for shift in range(0, 70, 7):
        if pos >= len(data):
            raise ValueError("truncated uvarint")
        byte = data[pos]
        pos += 1
        if shift == 63 and byte > 1:
            raise ValueError("overflow uvarint")
        value |= (byte & 127) << shift
        if byte < 128:
            return value, pos
    raise ValueError("overflow uvarint")


def go_string(data: bytes, pos: int):
    size, pos = uvarint(data, pos)
    if size > len(data) - pos:
        raise ValueError("truncated Go string")
    return data[pos:pos + size], pos + size


def build_info(data: bytes):
    magic = b"\xff Go buildinf:"
    pos = data.find(magic)
    if pos < 0 or pos + 32 > len(data):
        raise ValueError("Go build info not found")
    if data[pos + 14] != 8 or data[pos + 15] != 2:
        raise ValueError("unsupported build-info layout")
    version, cur = go_string(data, pos + 32)
    module, _ = go_string(data, cur)
    if len(module) < 33:
        raise ValueError("module framing missing")
    # Go debug/buildinfo module text has 16-byte sentinels on both ends.
    text = module[16:-16].decode("utf-8", errors="strict")
    rows = [line.split("\t") for line in text.splitlines()]
    return {
        "file_offset": pos, "go_version": version.decode("ascii"),
        "module_text": text, "records": rows,
        "vcs_settings_present": any(
            row[0] == "build" and len(row) > 1 and row[1].startswith("vcs.")
            for row in rows
        ),
    }


def pe_header(data: bytes):
    if data[:2] != b"MZ" or len(data) < 64:
        raise ValueError("not PE")
    off = struct.unpack_from("<I", data, 0x3C)[0]
    if off + 24 > len(data) or data[off:off + 4] != b"PE\0\0":
        raise ValueError("invalid PE signature")
    machine, count, _, _, _, opt_size, _ = struct.unpack_from("<HHIIIHH", data, off + 4)
    opt = off + 24
    if opt_size < 152 or opt + opt_size + count * 40 > len(data):
        raise ValueError("truncated PE optional/section headers")
    if struct.unpack_from("<H", data, opt)[0] != 0x20B:
        raise ValueError("not PE32+")
    cert_offset, cert_size = struct.unpack_from("<II", data, opt + 112 + 4 * 8)
    return {
        "machine_hex": hex(machine), "section_count": count,
        "certificate_table_offset": cert_offset, "certificate_table_bytes": cert_size,
        "certificate_chain_verification": "NOT RUN (no network or chain API)",
    }


def go_symbols(data: bytes):
    magic = b"\xf1\xff\xff\xff\0\0\1\10"
    candidates = []
    start = 0
    while True:
        pos = data.find(magic, start)
        if pos < 0:
            break
        start = pos + 8
        if pos + 72 > len(data):
            continue
        values = struct.unpack_from("<8Q", data, pos + 8)
        nf, nfiles, _, name, cu, filetab, pctab, pcln = values
        if (100 < nf < 100000 and 0 < nfiles < 100000 and
                72 <= name < cu <= filetab <= pctab <= pcln < len(data) - pos):
            candidates.append((pos, values))
    if len(candidates) != 1:
        raise ValueError("ambiguous or absent Go pcHeader")
    pos, values = candidates[0]
    nf, nfiles, _, name, cu, filetab, pctab, pcln = values
    names = [s.decode("utf-8", errors="strict") for s in
             data[pos + name:pos + cu].split(b"\0") if s]
    paths = [s.decode("utf-8", errors="strict") for s in
             data[pos + filetab:pos + pctab].split(b"\0") if s]
    return {"pc_header_offset": pos, "function_count_header": nf,
            "file_count_header": nfiles, "name_entries_including_inline": len(names),
            "project_names": [s for s in names if s.startswith(PREFIX)],
            "project_file_paths": [s for s in paths if s.startswith(PREFIX)],
            "network_names": [s for s in names if re.search(
                r"socksDialer|ProxyFromEnvironment|httpproxy|net\.\(\*Resolver\)\.(dial|lookup)|"
                r"net/http\.\(\*Transport\)\.dialConn$", s)]}


def excerpts(data: bytes):
    items = []
    start = data.index(b"## Outbound proxy environments\n")
    end = data.index(b"## Choose a deployment pattern", start)
    items.append({"kind": "EMBEDDED DOCUMENTATION (not executed behavior)",
                  "offset": start, "bytes": end - start,
                  "text": data[start:end].decode("utf-8")})
    literal = b"proxy URL scheme must be http or https, got %q"
    items.append({"kind": "BINARY ERROR LITERAL (branch not executed)",
                  "offset": data.index(literal), "bytes": len(literal),
                  "text": literal.decode("ascii")})
    return items


def main():
    sys.addaudithook(guard)
    raw = EXE.read_bytes()
    if sha(raw) != EXPECTED_SHA:
        raise ValueError("unexpected native executable hash")
    meta = json.loads((PREP / "official_release_metadata.json").read_text(encoding="utf-8"))
    asset = next(x for x in meta["assets"]
                 if x["name"] == "tunnel-client-v0.0.16-windows-amd64.zip")
    archive = PREP / "downloads" / asset["name"]
    zip_sha = sha(archive.read_bytes())
    sums = (PREP / "downloads/SHA256SUMS.txt").read_text(encoding="utf-8")
    published_sum = next(line.split()[0] for line in sums.splitlines()
                         if line.split()[-1].lstrip("*") == asset["name"])
    with zipfile.ZipFile(archive) as z:
        members = [x for x in z.infolist() if Path(x.filename).name == "tunnel-client.exe"]
        if len(members) != 1:
            raise ValueError("ambiguous executable in archive")
        zipped_sha = sha(z.read(members[0]))
        archive_names = z.namelist()
    info = build_info(raw)
    symbols = go_symbols(raw)
    sbom = json.loads((PREP / "tools/tunnel-client-v0.0.16-windows-amd64.spdx.json")
                      .read_text(encoding="utf-8"))
    packages = [{k: p.get(k) for k in ("SPDXID", "name", "versionInfo", "sourceInfo",
                                      "downloadLocation")}
                for p in sbom["packages"]
                if p.get("name") == "github.com/openai/tunnel-client" or
                ("/tunnel-client.exe" in p.get("sourceInfo", "") and
                 p.get("name") in {"golang.org/x/net", "golang.org/x/oauth2",
                                  "github.com/modelcontextprotocol/go-sdk"})]
    cached_version = (PREP / "version.txt").read_text(encoding="utf-8").strip()
    commit = re.search(r"git sha: ([a-f0-9]{40})", cached_version).group(1)
    result = {
        "task_id": "CODEX-WUA-0-DESKTOP-MCP-E2E-001", "amendment": "06",
        "exe": str(EXE), "exe_bytes": len(raw), "exe_sha256": sha(raw),
        "pe": pe_header(raw),
        "cached_cli_version": cached_version,
        "cli_executed_this_amendment": False,
        "commit_literal_offset": raw.find(commit.encode("ascii")),
        "version_commit_is_source_attestation": False,
        "release": {"tag": meta["tag_name"], "published_at": meta["published_at"],
                    "cached_release_url": meta["html_url"],
                    "zip_sha256": zip_sha,
                    "cached_release_digest_matches": asset["digest"] == "sha256:" + zip_sha,
                    "published_checksum_matches": zip_sha == published_sum,
                    "zip_executable_matches_installed": zipped_sha == sha(raw),
                    "archive_names": archive_names,
                    "remote_reverification": "NOT RUN (forbidden Git/GitHub operations)",
                    "independent_signature_or_build_attestation": "NOT AVAILABLE"},
        "build_info": {k: v for k, v in info.items() if k != "module_text"},
        "sbom_selected_packages": packages,
        "evidence_levels": {"identity": "VERIFIED AGAINST CACHED RELEASE",
                            "source_to_binary_correspondence": "NOT PROVEN",
                            "routing_semantics": "PARTIAL; docs/symbols/literals only",
                            "native_runtime": "NOT EXECUTED"},
        "native_transport_processes_started_by_this_audit": 0,
    }
    save("static_audit.json", result)
    save("binary_symbols.json", symbols)
    save("binary_excerpts.json", excerpts(raw))
    (OUT / "go_build_info.txt").write_text(info["go_version"] + "\n" + info["module_text"],
                                          encoding="utf-8")
    checks = result["release"]
    if not all(checks[k] for k in ("cached_release_digest_matches", "published_checksum_matches",
                                  "zip_executable_matches_installed")):
        raise ValueError("release integrity mismatch")
    print(json.dumps({"exe_sha256": sha(raw), "go": info["go_version"],
                      "project_file_paths": len(symbols["project_file_paths"]),
                      "project_name_entries": len(symbols["project_names"]),
                      "network_name_entries": len(symbols["network_names"]),
                      "native_processes_started": 0}))


if __name__ == "__main__":
    main()
