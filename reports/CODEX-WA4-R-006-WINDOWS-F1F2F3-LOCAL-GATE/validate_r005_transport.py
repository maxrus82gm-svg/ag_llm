"""Read-only newline transport adapter around the sealed R-005 validator.

Byte identity is mandatory: a candidate LF/CRLF restoration is accepted only
when its SHA-256 AND original length match the trusted manifest. No original
files or pins are rewritten. ZIPs are never normalized. All reconstruction is
in disposable TEMP, and the original source comparison remains enabled.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import tempfile

TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".txt"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def safe(base, relative):
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError("source path escapes root")
    return path


def restore(data, expected_sha, expected_size=None, *, text=False):
    def matches(candidate):
        return sha(candidate) == expected_sha and (expected_size is None or len(candidate) == expected_size)
    if matches(data):
        return data, "EXACT"
    if text:
        data.decode("utf-8")  # No encoding substitutions or ignored bytes.
        lf = data.replace(b"\r\n", b"\n")
        for mode, candidate in (("LF", lf), ("CRLF", lf.replace(b"\n", b"\r\n"))):
            if matches(candidate):
                return candidate, mode
    raise ValueError("content or binary identity mismatch; newline transport cannot restore trusted bytes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True, help="Trusted original R-005 seal, supplied independently")
    parser.add_argument("--simulate-lf", action="store_true", help="Normalize only in-memory/TEMP transport inputs")
    args = parser.parse_args()
    package = args.package.resolve()
    sources = args.sources.resolve()
    before = {}

    def read(path, *, text=False):
        data = path.read_bytes()
        before[str(path)] = sha(data)
        return data.replace(b"\r\n", b"\n") if args.simulate_lf and text else data

    manifest_raw, manifest_mode = restore(read(package / "manifest.json", text=True),
                                         args.manifest_sha256, text=True)
    manifest = strict_json(manifest_raw)
    modes = []
    source_modes = []
    with tempfile.TemporaryDirectory(prefix="wa4r006-r005-transport-") as temporary:
        base = Path(temporary)
        stage = base / "package"
        source_stage = base / "source"
        stage.mkdir(); source_stage.mkdir()
        (stage / "manifest.json").write_bytes(manifest_raw)
        transported = base / "transported"
        transported.mkdir()
        (transported / "manifest.json").write_bytes(manifest_raw)
        for name, pin in manifest["files"].items():
            eligible = Path(name).suffix in TEXT_SUFFIXES
            data = read(safe(package, name), text=eligible)
            target = safe(transported, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            original, mode = restore(data, pin["sha256"], pin["bytes"], text=eligible)
            target = safe(stage, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original)
            modes.append({"file": name, "mode": mode, "original_sha256": pin["sha256"], "original_bytes": pin["bytes"]})

        # Import only the validator whose exact original byte hash was checked.
        spec = importlib.util.spec_from_file_location("r005_sealed_validator", stage / "validate_export.py")
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        provenance = strict_json((stage / "provenance.json").read_bytes())
        source_pins = {item["path"]: item for item in provenance["inputs"]}
        for archive in provenance["archives"].values():
            if "parent" not in archive:
                source_pins[archive["path"]] = archive
        for name, pin in source_pins.items():
            eligible = Path(name).suffix in TEXT_SUFFIXES
            original, mode = restore(read(safe(sources, name), text=eligible), pin["sha256"], pin["bytes"], text=eligible)
            target = safe(source_stage, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original)
            source_modes.append({"path": name, "mode": mode})

        strict_transport = {"status": "PASS", "rejection": None}
        try:
            validator.validate(transported)
        except AssertionError as error:
            strict_transport = {"status": "REJECTED", "rejection": str(error)}
        recovered, _ = validator.validate(stage, source_stage)
        internal, _ = validator.validate(stage)
        assert recovered["manifest_checked"] and internal["manifest_checked"]
        controls = validator.adversarial(stage, provenance, source_stage)

        transport_controls = []
        entry = next((item for item in modes if item["mode"] != "EXACT"), modes[0])
        pin = manifest["files"][entry["file"]]
        changed = (stage / entry["file"]).read_bytes() + b"X"
        try:
            restore(changed, pin["sha256"], pin["bytes"], text=True)
        except ValueError:
            transport_controls.append({"control": "semantic byte changed", "observed": "REJECT", "status": "PASS"})
        else:
            raise AssertionError("newline normalization accepted a content change")
        binary = b"ZIP\r\nbytes"
        try:
            restore(binary.replace(b"\r\n", b"\n"), sha(binary), len(binary), text=False)
        except ValueError:
            transport_controls.append({"control": "binary normalization forbidden", "observed": "REJECT", "status": "PASS"})
        else:
            raise AssertionError("binary identity was normalized")
        for path, digest in before.items():
            assert sha(Path(path).read_bytes()) == digest, "original input changed"
        result = {
            "task": "CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE",
            "status": "PASS", "simulation": "LF transport" if args.simulate_lf else "actual local bytes",
            "trusted_manifest_sha256": args.manifest_sha256, "manifest_mode": manifest_mode,
            "strict_transport_before_restoration": strict_transport,
            "package_original_bytes_restored": sum(item["mode"] != "EXACT" for item in modes),
            "package_files": modes, "source_inputs": source_modes,
            "root_records_equal_to_original_zip": recovered["roots"], "manifest_checked": True,
            "original_inputs_unchanged": len(before), "export_controls": controls,
            "transport_controls": transport_controls,
            "runtime_acceptance": "NOT CLAIMED; evidence transport only",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
