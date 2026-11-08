"""Preserve every sanitized log version by original SHA; no private values are printed."""
import hashlib
import itertools
import json
from pathlib import Path
import tempfile

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
PRIVATE = Path(tempfile.gettempdir()) / (P.name + "_private_logs")
record = P / "evidence/sanitization.json"
data = json.loads(record.read_text(encoding="utf-8"))
home = str(Path.home())
choices = [home, home.replace("\\", "/"), home.replace("\\", "\\\\")]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
recovered = 0
for row in data["files"]:
    name = Path(row["path"]).name + "." + row["original_sha256"] + ".raw"
    dest = PRIVATE / name
    if not dest.exists():
        previous = PRIVATE / Path(row["path"]).name
        raw = previous.read_bytes() if previous.exists() else b""
        if sha(raw) != row["original_sha256"]:
            public = (ROOT / row["path"]).read_bytes()
            assert sha(public) == row["sanitized_sha256"], row["path"]
            text = public.decode("utf-8")
            parts = text.split("<USER_HOME>")
            # Most logs are uniformly JSON-escaped or plain Windows paths.
            attempts = [tuple(value for _ in parts[1:]) for value in choices]
            spans = []
            for offset in [0, text.rfind('{"secret_guard":')]:
                if offset >= 0:
                    try:
                        _, end = json.JSONDecoder().raw_decode(text[offset:])
                        spans.append((offset, offset + end))
                    except ValueError:
                        pass
            positions = [m.start() for m in __import__("re").finditer("<USER_HOME>", text)]
            attempts += [tuple(inside if any(a <= pos < b for a, b in spans) else outside for pos in positions)
                         for inside, outside in itertools.product(choices, repeat=2)]
            if len(parts) <= 10:
                attempts = itertools.chain(attempts, itertools.product(choices, repeat=len(parts) - 1))
            for replacement in attempts:
                candidate = parts[0] + "".join(value + tail for value, tail in zip(replacement, parts[1:]))
                raw = candidate.encode("utf-8")
                if sha(raw) == row["original_sha256"]:
                    recovered += 1
                    break
            else:
                raise AssertionError("cannot verify original log " + row["path"])
        dest.write_bytes(raw)
    assert sha(dest.read_bytes()) == row["original_sha256"]
    row["original"] = "private TEMP / " + P.name + "_private_logs / " + name
record.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"original_versions_verified": len(data["files"]), "sha_verified_reconstructions": recovered,
                  "values_printed": False}))
