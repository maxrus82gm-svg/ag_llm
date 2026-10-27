"""Build a bounded text review packet and hash the local documentation package.

Does not apply candidates or change project documents. No Git/network operations.
"""
from pathlib import Path
import difflib
import hashlib
import json
import sys

WORK = Path(__file__).resolve().parents[1]
ROOT = WORK.parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(name):
    return json.loads((WORK / name).read_text(encoding="utf-8"))


def packet():
    assert not (WORK / "review_packet.txt").exists(), "Preserve the exact transmitted review packet"
    base = load("evidence/baseline.json")
    items = ["""НЕЗАВИСИМЫЙ REVIEW: ASTRA-DOC-CONTEXT-OPTIMIZATION-001, продолжение 27.10.2026

Пользователь первоначально заказал только проект, затем прямо поручил самостоятельно применить каркасы и правила по всему проекту и подтвердил полномочия в текущем чате без нового БЛОКА 1. Этот пакет относится к последней локальной редакции, а №41 остаётся исходным предложением. Пользователь ранее поручил передать результат ChatGPT на независимую проверку.

Просьба проверить связность, полноту и применимость правил к роли ChatGPT-планировщика/проверяющего/закрывающего. Не изменять проект, не использовать Git/GitHub, не закрывать TASK и не выдавать авторские проверки за собственную проверку файлов. Независимость ограничена: здесь переданы точные выбранные фрагменты локальных документов и авторские evidence, но не все полные исходные snapshots. Если файлы/публикация недоступны, пометить FILE VERIFICATION PENDING. Требуется текстовый verdict PASS/REVISE/FAIL только для явно указанного scope, замечания с адресами и перечень непроверенного. Для наблюдений предпочитать точный DOC ID / раздел / поле.

Проверить особенно:
1. Новый обычный чат входит через №08 и восстанавливает цель/статус/OPEN/NEXT без чтения всей истории; BLIND-START не получает чужой контекст.
2. Релизный ChatGPT получает явные действия и формы: приёмка, публикация, история/readback, риски, №34/40, карточка последней. Авторский PASS не становится независимым VERIFIED.
3. Состояния риска, owner/verifier, evidence, неопределённость и условия закрытия не создают ложной уверенности.
4. Устойчивые record ID / TASK ID / заголовок / hash вместо номера строки как единственного адреса. Текстовые указатели не объявляются графовыми связями.
5. Переполнение уменьшает рабочую загрузку переносом проверенной истории, без потери единственного экземпляра. Старые CURRENT в сохранённых адресах не считаются текущим authority.
6. Не изменены права технических задач, paid/live/B2/WA4-R/MCP freeze. Прямое разрешение на эту документационную работу не стало универсальным разрешением.

Ниже: итоговый отчёт, авторский разбор сценариев, фактические рабочие фрагменты 13 документов и результаты проверок. Разделы после «Сохранённые адреса прежней редакции», старые БЛОКИ 1–4, полные №05/06 и старый корпус №18 в этот текст не включены; их побайтовая сохранность заявлена авторскими evidence, независимо здесь не доказана. Полный локальный комплект: reports/ASTRA-DOC-CONTEXT-OPTIMIZATION-001/implementation-20261027/.
"""]
    for name in ("report.md", "scenario_review.md"):
        items.append("\n=== " + name + " ===\n" + (WORK / name).read_text(encoding="utf-8"))
    for entry in base["targets"]:
        path = ROOT / entry["source"]
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig").replace("\r\n", "\n")
        original = (ROOT / entry["snapshot"]).read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
        name = path.name
        if name.startswith(("000_Задачи ChatGPT", "000_Задачи Claude", "000_Задачи Codex", "000_Задачи Ultra")):
            excerpt = text.split("# БЛОК 1", 1)[0]
            scope = "Точные Правила до неизменённых персональных БЛОКОВ 1–4"
        elif name.startswith(("000_Задачи для", "07_", "08_", "34_")):
            excerpt = text.split("## Сохранённые адреса прежней редакции", 1)[0]
            scope = "Точная рабочая часть; исторические адреса совместимости исключены"
        elif name.startswith(("05_", "06_")):
            assert text.endswith(original)
            excerpt = text[:-len(original)]
            scope = "Точный новый вход; исходный документ неизменным суффиксом исключён"
        else:
            excerpt = "".join(difflib.unified_diff(original.splitlines(keepends=True), text.splitlines(keepends=True), fromfile="preserved/" + name, tofile="applied/" + name, n=3))
            scope = "Точная текстовая дельта Python difflib; Git не использовался"
        items.append("\n=== " + entry["source"] + " ===\nПолный файл SHA-256: " + digest(raw) + "\nScope: " + scope + "\n\n" + excerpt)
    for name in ("evidence/framework_checks.json", "evidence/applied_readback.json"):
        items.append("\n=== " + name + " (AUTHOR EVIDENCE) ===\n" + (WORK / name).read_text(encoding="utf-8"))
    result = "\n".join(items)
    (WORK / "review_packet.txt").write_text(result, encoding="utf-8", newline="\n")
    print(json.dumps({"review_packet_chars": len(result), "review_packet_bytes": len(result.encode("utf-8"))}))


def finalize():
    state = load("evidence/applied_readback.json")
    for entry in state["targets"]:
        assert digest((ROOT / entry["path"]).read_bytes()) == entry["sha256"], entry["path"]
    paths = [ROOT / entry["path"] for entry in state["targets"]]
    paths += [p for p in WORK.rglob("*") if p.is_file() and p != WORK / "manifest.json" and "__pycache__" not in p.parts]
    entries = []
    for p in sorted(set(paths)):
        raw = p.read_bytes()
        entries.append({"path": p.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": digest(raw)})
    value = {"task_id": "ASTRA-DOC-CONTEXT-OPTIMIZATION-001", "phase": "implementation-20261027", "status": "LOCAL DOCUMENTATION APPLIED / AWAITING INDEPENDENT REVIEW", "path_base": "workspace root M:/GitHub/ag_llm", "hash_algorithm": "SHA-256", "manifest_self_excluded": True, "entries": entries}
    (WORK / "manifest.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    verify()


def verify():
    manifest = load("manifest.json")
    entries = manifest["entries"]
    assert len(entries) == len({x["path"] for x in entries}), "Duplicate manifest paths"
    for entry in entries:
        path = ROOT / entry["path"]
        assert path.is_file(), entry["path"]
        raw = path.read_bytes()
        assert len(raw) == entry["bytes"] and digest(raw) == entry["sha256"], entry["path"]
    expected = {p.relative_to(ROOT).as_posix() for p in WORK.rglob("*") if p.is_file() and p != WORK / "manifest.json" and "__pycache__" not in p.parts}
    expected |= {x["path"] for x in load("evidence/applied_readback.json")["targets"]}
    assert expected == {x["path"] for x in entries}, "Manifest scope mismatch"
    receipt_path = WORK / "handoff_receipt.json"
    if receipt_path.exists():
        sent = load("handoff_receipt.json")["packet"]
        raw = (ROOT / sent["path"]).read_bytes()
        assert digest(raw) == sent["sha256"] and len(raw) == sent["bytes"], "Sent packet changed"
        assert len(raw.decode("utf-8")) == sent["characters"], "Sent packet length changed"
    print(json.dumps({"manifest_entries": len(entries), "hashes_verified": len(entries), "missing": 0, "mismatches": 0, "status": "PASS"}))


if __name__ == "__main__":
    {"packet": packet, "finalize": finalize, "verify": verify}[sys.argv[1]]()
