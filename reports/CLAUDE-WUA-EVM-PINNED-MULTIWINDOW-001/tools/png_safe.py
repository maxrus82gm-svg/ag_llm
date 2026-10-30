"""Make the PNG screenshots of the package pass the publication scan without changing a single pixel.

web_alarm.evidence_sanitizer reads a binary file through text views (latin-1, UTF-16) and refuses it when they show a
path or a local name. Compressed PNG data sometimes shows such letters by pure chance. For every screenshot the scan does
not pass as CLEAN, the image data (IDAT) is decompressed and compressed again with other zlib settings until the scan is
CLEAN; the decompressed image data must stay byte-identical (same pixels). Other chunks are kept as they are.
Usage: png_safe.py <package folder> <out.json>
"""
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SIGNATURE = b"\x89PNG\r\n\x1a\n"
sha = lambda data: hashlib.sha256(data).hexdigest()


def chunks(data: bytes):
    assert data[:8] == SIGNATURE, "not a PNG"
    i = 8
    while i < len(data):
        n = struct.unpack(">I", data[i:i + 4])[0]
        yield data[i + 4:i + 8], data[i + 8:i + 8 + n]
        i += 12 + n


def build(parts) -> bytes:
    out = bytearray(SIGNATURE)
    for kind, body in parts:
        out += struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    return bytes(out)


def image_data(data: bytes) -> bytes:
    return zlib.decompress(b"".join(body for kind, body in chunks(data) if kind == b"IDAT"))


def scan(name: str, data: bytes, package: str) -> dict:
    folder = Path(tempfile.mkdtemp(prefix="claude-evmpins-png-")) / package
    folder.mkdir()
    (folder / name).write_bytes(data)
    try:
        done = subprocess.run([sys.executable, "-B", "-m", "web_alarm.evidence_sanitizer", "--repo-anchor", "ag_llm", "scan", str(folder)],
                              cwd=REPO, capture_output=True, text=True, encoding="utf-8")
        return {"exit": done.returncode, "classes": json.loads(done.stdout)["classes"]}
    finally:
        shutil.rmtree(folder.parent, ignore_errors=True)


def recompress(data: bytes, level: int, strategy: int, mem: int) -> bytes:
    parts = list(chunks(data))
    packer = zlib.compressobj(level, zlib.DEFLATED, 15, mem, strategy)
    idat = packer.compress(image_data(data)) + packer.flush()
    first = next(i for i, (kind, _) in enumerate(parts) if kind == b"IDAT")
    rest = [p for p in parts if p[0] != b"IDAT"]
    return build(rest[:first] + [(b"IDAT", idat)] + rest[first:])


def main():
    package, target = Path(sys.argv[1]), Path(sys.argv[2])
    rows = []
    for path in sorted((package / "evidence" / "screenshots").glob("*.png")):
        original = path.read_bytes()
        first = scan(path.name, original, package.name)
        row = {"file": path.name, "first_scan": first["classes"], "original_sha256": sha(original), "changed": False}
        if first["classes"] != {"CLEAN": 1}:
            tried = 0
            for level in (9, 8, 7, 6, 5, 4, 3, 2, 1):
                for strategy in (zlib.Z_DEFAULT_STRATEGY, zlib.Z_FILTERED, zlib.Z_RLE):
                    for mem in (9, 8):
                        tried += 1
                        candidate = recompress(original, level, strategy, mem)
                        if image_data(candidate) != image_data(original):
                            sys.exit(f"{path.name}: the image data changed")
                        if scan(path.name, candidate, package.name)["classes"] == {"CLEAN": 1}:
                            path.write_bytes(candidate)
                            row.update(changed=True, zlib={"level": level, "strategy": strategy, "memLevel": mem}, attempts=tried)
                            break
                    if row["changed"]:
                        break
                if row["changed"]:
                    break
            if not row["changed"]:
                sys.exit(f"{path.name}: no clean encoding found")
        final = path.read_bytes()
        row.update(final_sha256=sha(final), image_data_sha256=sha(image_data(final)), same_pixels=image_data(final) == image_data(original),
                   final_scan=scan(path.name, final, package.name)["classes"])
        rows.append(row)
        print(json.dumps({k: row[k] for k in ("file", "first_scan", "changed", "final_scan")}), flush=True)
    record = {"task": "CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001", "purpose": "screenshots made scan-clean by a lossless PNG re-compression",
              "files": rows, "changed": sum(r["changed"] for r in rows), "all_same_pixels": all(r["same_pixels"] for r in rows),
              "all_clean": all(r["final_scan"] == {"CLEAN": 1} for r in rows)}
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: record[k] for k in ("changed", "all_same_pixels", "all_clean")}))


if __name__ == "__main__":
    main()
