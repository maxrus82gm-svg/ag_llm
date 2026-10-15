"""Read-only R-006 RAW/ZIP/manifest verification; no production imports."""
from pathlib import Path
import argparse
import hashlib
import json
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def load(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def safe(name):
    path = (HERE / name).resolve()
    assert path.is_relative_to(HERE.resolve()), "Package path traversal"
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-check", type=Path)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    provenance = load((HERE / "provenance.json").read_bytes())
    checks = load((HERE / "checks.json").read_bytes())
    pin = provenance["archive"]
    archive_bytes = safe(pin["file"]).read_bytes()
    assert len(archive_bytes) == pin["bytes"] and sha(archive_bytes) == pin["sha256"]
    entries = [load(line) for line in (HERE / "raw-index.jsonl").read_bytes().splitlines()]
    assert len(entries) == checks["raw_records"] == len({entry["id"] for entry in entries})
    with zipfile.ZipFile(safe(pin["file"])) as archive:
        assert archive.testzip() is None
        assert archive.namelist() == [item["member"] for item in pin["inventory"]]
        for item in pin["inventory"]:
            data = archive.read(item["member"])
            assert len(data) == item["bytes"] and sha(data) == item["sha256"]
        for entry in entries:
            data = safe(entry["file"]).read_bytes()
            assert len(data) == entry["text_bytes"] and sha(data) == entry["text_sha256"]
            value = load(data)
            assert value["origin"] == {k: v for k, v in entry.items() if k not in ("text_bytes", "text_sha256")}
            member = archive.read(entry["member"])
            assert sha(member) == entry["member_sha256"] and len(member) == entry["member_bytes"]
            original = load(member)["tests"][int(entry["pointer"].split("/")[-1])]
            assert canonical(value["raw"]) == canonical(original)
            assert sha(canonical(original)) == entry["canonical_record_sha256"]
            assert original["test"] == entry["selector"] and original["status"] == entry["original_status"]
        for run in checks["runs"]:
            result = load(archive.read(run["member"]))
            assert sum(result[key] for key in ("passed", "failures", "errors", "skips")) == result["tests_run"]
            assert result["tests_run"] == len(result["tests"])
            for status, key in (("PASS", "passed"), ("FAIL", "failures"), ("ERROR", "errors"), ("SKIP", "skips")):
                assert sum(test["status"] == status for test in result["tests"]) == result[key]
                assert run[key] == result[key]
    source_checked = 0
    if args.source_check:
        for name, digest in checks["final_full_source_sha256"].items():
            path = (args.source_check / name).resolve()
            assert path.is_relative_to(args.source_check.resolve())
            assert sha(path.read_bytes()) == digest, "Local source drift: " + name
            source_checked += 1
    manifest_checked = False
    if (HERE / "manifest.json").exists():
        manifest = load((HERE / "manifest.json").read_bytes())
        actual = {p.relative_to(HERE).as_posix() for p in HERE.rglob("*") if p.is_file()
                  and p.name != "manifest.json" and "__pycache__" not in p.parts}
        assert actual == set(manifest["files"])
        for name, file_pin in manifest["files"].items():
            data = safe(name).read_bytes()
            assert len(data) == file_pin["bytes"] and sha(data) == file_pin["sha256"]
        manifest_checked = True
    control = "NOT RUN"
    if args.self_check:
        with tempfile.TemporaryDirectory(prefix="wa4r006-package-control-") as directory:
            entry = entries[0]
            value = load(safe(entry["file"]).read_bytes())
            value["raw"]["status"] = "FORGED_SUCCESS"
            changed = Path(directory) / "changed.json"
            changed.write_bytes(canonical(value))
            assert sha(changed.read_bytes()) != entry["text_sha256"]
            assert sha(canonical(value["raw"])) != entry["canonical_record_sha256"]
        control = "PASS: changed RAW status rejected by byte and canonical pins"
    print(json.dumps({"status": "PASS", "raw_records": len(entries), "archive_crc": "PASS",
                      "final_local_source_files_checked": source_checked,
                      "manifest_checked": manifest_checked, "integrity_negative_control": control}))


if __name__ == "__main__":
    main()
