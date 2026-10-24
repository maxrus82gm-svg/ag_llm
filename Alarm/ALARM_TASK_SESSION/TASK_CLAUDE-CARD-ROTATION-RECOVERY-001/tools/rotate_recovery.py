"""CARD ROTATION RECOVERY for CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001 (chat-only service order of 2026-10-24).

precheck  read-only: card markers and line endings; BLOCK 1 still byte-equal (LF-normalised) to the statement archived by
          rotate_finalize; the archived statement is present in that record; this TASK's lines in BLOCK 2/3; 5/5 entries;
          hashes of Rules / BLOCK 4; read back exactly this TASK's three earlier 001 records by their receipts and the
          last two bytes of 001 - no other archive content is read or searched.
A         append the missing CHAT-ONLY AMENDMENT record (+ this service order) to 001; read back exactly the appended
          byte range; prove the earlier archive bytes are unchanged.
B         re-verify, then replace this TASK's line in BLOCK 2 and BLOCK 3 in place and set BLOCK 1 to WAITING; Rules and
          BLOCK 4 must stay byte-identical; the archive must stay as after A.
Usage: rotate_recovery.py precheck <state.json> | A <state.json> | B <state.json>
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]
DOCS = ROOT / "Документация"
CARD = DOCS / "000_Задачи Claude.md"
ARCHIVE = DOCS / "001_История выполненных задач Claude.md"
TASK = "CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001"
PKG = ROOT / "Alarm" / "ALARM_TASK_SESSION" / f"TASK_{TASK}"
PKG_REL = f"Alarm/ALARM_TASK_SESSION/TASK_{TASK}"
OWN_REL = "Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-CARD-ROTATION-RECOVERY-001"
H1 = "---\n# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n---\n\n"
H2 = "---\n# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)\n"
H3 = "# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ\n"
H4 = "# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER\n"
WAITING = "Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ\nTASK: —\n\n"
RECEIPTS = ("card-rotation.json", "amendment-rotation.json", "finalize-rotation.json")
FINALIZE_BLOCK1_SHA = "406882545660c3c30de15ab7de4e23aa70607e8dba54b2290ec24bef43bc9567"
ARCHIVE_SIZE = 714314
PREFIX2 = f"- **2026-10-23 / {TASK}**"
PREFIX3 = f"- **{TASK}**"
LINE2_BEFORE = (f"{PREFIX2} — исправление fail-open F-ES-01 / F-ES-02 + REVISE F-ES-03 (2026-10-24) + локальное "
                "завершение пакета (SHA-256/manifest/mapping, 2026-10-24). Статус: RESULT READY / AWAITING INDEPENDENT "
                "VERIFICATION.")
LINE3_BEFORE = (f"{PREFIX3} — F-ES-01/F-ES-02 закрыты fail-closed; REVISE F-ES-03: `--package` = комплект, внутри или "
                "вокруг него, через ссылку или жёсткие ссылки → `package-not-independent`, REFUSED; завершение: 201 "
                "CRLF-копия прогона не сверялась бы с опубликованным блобом → копии в LF, manifest отказывает при CR, "
                f"`evidence.json` исправлен, `tools/check_package.py` CONSISTENT. Полный источник: записи в `001` и "
                f"`{PKG_REL}/report.md`.")
LINE2 = (f"{PREFIX2} — исправление fail-open F-ES-01 / F-ES-02 + REVISE F-ES-03 (2026-10-24) + локальное завершение "
         "пакета (SHA-256/manifest/mapping, 2026-10-24) + CHAT-ONLY AMENDMENT: дубликаты `id` в `runs-map.json` "
         "(2026-10-24). Статус исполнителя: RESULT READY; независимо (БЛОК 4, 2026-10-24): PASS / BOUNDED OFFLINE "
         "VERIFIED.")
LINE3 = (f"{PREFIX3} — F-ES-01/F-ES-02 закрыты fail-closed; REVISE F-ES-03: `--package` = комплект, внутри или вокруг "
         "него, через ссылку или жёсткие ссылки → `package-not-independent`, REFUSED; завершение: 201 CRLF-копия прогона "
         "не сверялась бы с опубликованным блобом → копии в LF, manifest отказывает при CR, `evidence.json` исправлен; "
         "CHAT-ONLY AMENDMENT: `tools/check_package.py` — уникальность `id` в `runs-map`, строгая загрузка JSON (повтор "
         "ключа), безопасный `id`, самотест 11/11 DETECTED, пакет CONSISTENT. Полный источник: записи в `001` и "
         f"`{PKG_REL}/report.md` (§12–14).")
sha = lambda data: hashlib.sha256(data).hexdigest()


def load_card():
    data = CARD.read_bytes()
    crlf = data.count(b"\r\n")
    assert data.count(b"\r") == crlf and (crlf == 0 or data.count(b"\n") == crlf), "mixed line endings: STOP"
    eol = "\r\n" if crlf else "\n"
    text = data.decode("utf-8").replace("\r\n", "\n")
    for marker in (H1, H2, H3, H4):
        assert text.count(marker) == 1, f"marker not unique: {marker!r}"
    assert text.index(H1) < text.index(H2) < text.index(H3) < text.index(H4), "marker order: STOP"
    return data, text, eol


def regions(text):
    return (text[:text.index(H1)], text[text.index(H1) + len(H1):text.index(H2)],
            text[text.index(H2):text.index(H3)], text[text.index(H3):text.index(H4)], text[text.index(H4):])


def own_line(block, prefix):
    lines = [line for line in block.split("\n") if line.startswith(prefix)]
    assert len(lines) == 1, f"expected exactly one line for this TASK: {prefix}"
    return lines[0]


def entries(block):
    return [line for line in block.split("\n") if line.startswith("- **")]


def read_range(offset, length):
    with open(ARCHIVE, "rb") as handle:
        handle.seek(offset)
        return handle.read(length)


def verbatim(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
    assert "```" not in text, f"fence inside {path.name}: STOP"
    return text


def build_record():
    amend = verbatim(PKG / "amendment-check-package-duplicates.md")
    order = verbatim(HERE / "service-order.md")
    amend_result = verbatim(HERE / "amendment-result.md")
    recovery_result = verbatim(HERE / "recovery-result.md")
    return (
        f"\n---\n\n## 2026-10-24 — {TASK} — CHAT-ONLY AMENDMENT: ДУБЛИКАТЫ `id` В `runs-map.json` + CARD ROTATION "
        "RECOVERY\n\n"
        "**НЕПРОВЕРЕННАЯ АРХИВНАЯ СЕКЦИЯ** (дополнение к записям этой TASK от 2026-10-23 и 2026-10-24; факт "
        "исполнителя, независимая приёмка — БЛОК 4 / 06). **Исходный статус:** RESULT READY / AWAITING INDEPENDENT "
        f"VERIFICATION. **Отчёт:** `{PKG_REL}/report.md` (раздел 14); текст AMENDMENT — "
        f"`{PKG_REL}/amendment-check-package-duplicates.md`; ротация — `{OWN_REL}/report.md`. Оба поручения получены "
        "в чате исполнителя без собственного TASK ID.\n\n"
        f"### CHAT-ONLY AMENDMENT дословно\n\n```text\n{amend}\n```\n\n"
        f"### Фактический результат AMENDMENT\n\n{amend_result}\n\n"
        f"### Служебное распоряжение CARD ROTATION RECOVERY дословно\n\n```text\n{order}\n```\n\n"
        f"### Фактический результат ротации\n\n{recovery_result}\n"
    )


phase = sys.argv[1]
state_path = Path(sys.argv[-1])
data, text, eol = load_card()
rules, block1, block2, block3, block4 = regions(text)
if phase == "precheck":
    receipts = [json.loads((PKG / name).read_text(encoding="utf-8")) for name in RECEIPTS]
    ranges = [(r["archive_offset"], r["archive_appended_bytes"], r["archive_record_sha256"]) for r in receipts]
    readbacks = [sha(read_range(o, n)) == s for o, n, s in ranges]
    contiguous = all(ranges[i][0] + ranges[i][1] == ranges[i + 1][0] for i in range(len(ranges) - 1)) \
        and ranges[-1][0] + ranges[-1][1] == ARCHIVE_SIZE
    size = ARCHIVE.stat().st_size
    tail = read_range(max(0, size - 2), 2)
    statement = "\n".join(line.rstrip() for line in block1.strip("\n").split("\n"))
    finalize_record = read_range(ranges[2][0], ranges[2][1]).decode("utf-8").replace("\r\n", "\n")
    own_records = "".join(read_range(o, n).decode("utf-8") for o, n, _ in ranges)
    state = {"phase": "precheck", "card_sha256": sha(data), "card_bytes": len(data),
             "card_eol": "CRLF" if eol == "\r\n" else "LF",
             "block1_sha256": sha(block1.encode()), "block1_equals_archived_finalize_block1":
                 sha(block1.encode()) == FINALIZE_BLOCK1_SHA,
             "block1_statement_in_finalize_record": f"```text\n{statement}\n```" in finalize_record,
             "rules_sha256": sha(rules.encode()), "rules_equal_to_last_rotation":
                 sha(rules.encode()) == receipts[2]["rules_sha256"],
             "block4_sha256": sha(block4.encode()), "block4_changed_since_last_rotation_by_verifier":
                 sha(block4.encode()) != receipts[2]["block4_sha256"],
             "line2_matches_last_rotation": own_line(block2, PREFIX2) == LINE2_BEFORE,
             "line3_matches_last_rotation": own_line(block3, PREFIX3) == LINE3_BEFORE,
             "block2_entries": len(entries(block2)), "block3_entries": len(entries(block3)),
             "earlier_records_readback": readbacks, "earlier_records_contiguous_to_end": contiguous,
             "duplicates_amendment_already_archived": "40084806720" in own_records,
             "archive_size": size, "archive_sha256": sha(ARCHIVE.read_bytes()),
             "archive_eol": "CRLF" if tail == b"\r\n" else "OTHER",
             "archive_read": "own three record ranges (by receipts) + last 2 bytes; whole-file hash only"}
    checks = (state["block1_equals_archived_finalize_block1"], state["block1_statement_in_finalize_record"],
              state["line2_matches_last_rotation"], state["line3_matches_last_rotation"],
              state["block2_entries"] == 5, state["block3_entries"] == 5, all(readbacks), contiguous,
              size == ARCHIVE_SIZE, state["archive_eol"] == "CRLF", not state["duplicates_amendment_already_archived"])
    state["result"] = "OK" if all(checks) else "STOP"
    build_record()  # fences / inputs must be valid before anything is written
elif phase == "A":
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["phase"] == "precheck" and state["result"] == "OK" and state["card_sha256"] == sha(data), "drift"
    before = ARCHIVE.read_bytes()
    assert len(before) == state["archive_size"] and sha(before) == state["archive_sha256"], "archive changed: STOP"
    payload = build_record().replace("\n", "\r\n").encode("utf-8")
    with open(ARCHIVE, "ab") as handle:
        handle.write(payload)
    after = ARCHIVE.read_bytes()
    back = read_range(len(before), len(payload))
    assert back == payload and after[:len(before)] == before and len(after) == len(before) + len(payload), \
        "archive readback mismatch: CARD ROTATION BLOCKED"
    state.update(phase="A", archive_offset=len(before), archive_appended_bytes=len(payload),
                 archive_record_sha256=sha(payload), archive_size_after=len(after),
                 archive_sha256_after=sha(after), readback="MATCH", earlier_bytes_unchanged=True)
elif phase == "B":
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["phase"] == "A" and state["card_sha256"] == sha(data), "card changed since precheck: STOP"
    assert sha(ARCHIVE.read_bytes()) == state["archive_sha256_after"], "archive changed since A: STOP"
    assert sha(read_range(state["archive_offset"], state["archive_appended_bytes"])) == state["archive_record_sha256"]
    new_text = rules + H1 + WAITING + block2.replace(LINE2_BEFORE, LINE2) + block3.replace(LINE3_BEFORE, LINE3) + block4
    CARD.write_bytes(new_text.replace("\n", eol).encode("utf-8"))
    disk, disk_text, disk_eol = load_card()
    d_rules, d_block1, d_block2, d_block3, d_block4 = regions(disk_text)
    assert disk_eol == eol and d_block1 == WAITING
    assert own_line(d_block2, PREFIX2) == LINE2 and own_line(d_block3, PREFIX3) == LINE3
    assert len(entries(d_block2)) == 5 and len(entries(d_block3)) == 5
    assert (sha(d_rules.encode()), sha(d_block4.encode())) == (state["rules_sha256"], state["block4_sha256"])
    assert sha(ARCHIVE.read_bytes()) == state["archive_sha256_after"]
    state.update(phase="B", card_after_sha256=sha(disk), card_after_bytes=len(disk), card_after_eol=state["card_eol"],
                 block1_now="WAITING", block2_entries_after=5, block3_entries_after=5, rules_unchanged=True,
                 block4_sha256_after=sha(d_block4.encode()), block4_unchanged=True, archive_unchanged_after_B=True)
else:
    raise SystemExit("phase must be precheck, A or B")
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(state, ensure_ascii=True, indent=1))
