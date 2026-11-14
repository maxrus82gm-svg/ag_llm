# H34 precloseout snapshot: original БЛОКИ 2–4

Source: Документация/000_Задачи Codex.md, main@74fc4b545221af95adc079d4ce68a0dc381de5c8. Only blocks 2–4 are archived; blocks 1 and 1.1 remain immutable.

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Полный предыдущий БЛОК 2–4 `reports/CHATGPT-WEB29-H33-REVIEW-20261113/prior_closeout_snapshot.md`; БЛОКИ 1/1.1 неизменны; подробнее №001 Codex/№05/адресная запись.

- **13.11 / H-CODEX-000033:** HTTP GigaChat MockTransport + exact wire, независимые Windows 18+36 PASS; REAL HOLD.
- **13.11 / H-CODEX-000032:** Ordinary fake one-send S2/S3a/Turn/RAW OFFLINE PASS.
- **12.11 / H-CODEX-000031:** launcher guard 21 PASS, physical CMD/F5 NOT RUN.
- **10.11 / H-CODEX-000030:** read-only pre-send review 7 PASS, full S3b OPEN.
- **10.11 / H-CODEX-000029:** per-chat settings/usage, user GUI PASS, provider caps OPEN.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **H33:** GigaChat-shaped MockTransport exact bytes→S2/S3a→one synthetic HTTP→terminal/Turn/RAW/usage/reopen; independent CI 43478748679: 18+36, regression236+220, S2 73, isolation52+5, UI57 PASS, 2 expected RED; S1 RAW NOT RUN, REAL factory absent.
- **H32:** accepted only one fake send, no real transport admission.
- **H31:** launcher F-01 defended, physical GUI NOT RUN.
- **H30:** READ-ONLY preflight PASS; broad S3b not verified.
- **H29:** per-chat preferences supported; real caps unverified.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА
---

## WEB29 / 13.11.2026 — H-CODEX-000033 — GigaChat MockTransport bounded independent PASS

**TASK:** `CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001`, source `main@56e7f33c351624de94db77e080767930b8cf3d38` №592; CI-only `GPT@397040862b63fb23f7f3b51e1e1e1d793fee5179` №593. Independent [Windows run 43478748679](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43478748679) **SUCCESS**, job 132069412034, artifact 14062849789 (29 files): H33 **18 PASS + 36 subtests**, H32/core regression **236 PASS + 220 subtests**, S2 **73 PASS**, isolation **52 PASS + 5 subtests**, Node UI **57 PASS**, **2 expected RED**, unexpected guards 0. Exact-wire/ledger/terminal/reopen verified in synthetic `httpx.MockTransport`, real_available=false. **VERDICT: PASS / H33 DOC CLOSED STRICTLY BOUNDED INDEPENDENT WINDOWS OFFLINE.** Historical S1 pinned RAW NOT RUN (author 69 is not independent), physical CMD/browser/F5 NOT RUN, real provider caps/OAuth/paid, all-route S3b/S3c/S9/S13a, old-audit migration/capacity and host fencing OPEN. **REAL/Stage6 full/Stage7 HOLD**, no user live GO. Review `reports/CHATGPT-WEB29-H33-REVIEW-20261113/review.md`, №06 `EVT-WEB29-H33-MOCK-HTTP-CLOSEOUT-20261113`. БЛОК 1 WAITING, БЛОК 1.1 immutable H33.

## WEB28 / 13.11.2026 — H-CODEX-000032 — прежний bounded independent OFFLINE PASS

Ordinary fake one-send; independent Windows runs 43417573566 and 43416113378 SUCCESS, 236/74/52/57 and two expected RED. Full `reports/CHATGPT-WEB28-H32-REVIEW-20261113/review.md`, №06; no REAL/full S3b.

## WEB29 / 12.11.2026 — H-CODEX-000031 — прежний bounded independent OFFLINE PASS

TEST launcher F-01 Windows independent 21 PASS, physical CMD/browser/F5 NOT RUN. Full `reports/CHATGPT-WEB29-H31-F01-REVIEW-20261112/review.md`, №06.

**Снимок вытесненной старой записи H30 и БЛОКОВ 2–4:** `reports/CHATGPT-WEB29-H33-REVIEW-20261113/prior_closeout_snapshot.md`; исходные evidence/№06 сохранены.
