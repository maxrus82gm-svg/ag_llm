# WUA WFP backend — offline source candidate

**RESULT READY / AWAITING INDEPENDENT VERIFICATION (WEB_11).**
Это самостоятельный пакет исходников и offline-проверок, а не системный installer.
`CanApply=false`; прежний toolkit и его безусловный BLOCKED не изменены.

Состав:

- `source/Core.cs`: immutable typed request/policy, deny builder, независимый
  schema verifier, content binding, conservative admission/arbitration diagnostics,
  только in-memory transaction exercise.
- `source/Abi.cs`, `SdkConstants.cs`: точные x64 структуры и managed marshalling,
  SID security descriptor, bounded object readback comparison. **Нет P/Invoke**.
- `native/NativePreview.cs`: отдельная неактивная сборка с 15 настоящими Fwpm
  declarations, transaction/provider/sublayer/filter stage и readback source.
  Нет exported public types/entrypoint. Не используется runtime-компонентами.
  Rollback delete не реализован и остаётся BLOCKED.
- `tests/`: .NET synthetic runner, C++ compile-only ABI assertions,
  адресная проверка чистых gate функций прежнего toolkit.
- `contracts/`, `security_boundary.md`, `lab_gate.md`, `integration_plan.md`:
  конкретные ограничения и будущие независимые gates.

## Воспроизведение без установки зависимостей

Нужны **уже установленные** .NET Framework 4.5+ x64/C# compiler, MSVC C++ и
Windows SDK. Текущие orchestration helpers используют существующий Python 3;
ни NuGet, ни dotnet restore, ни Pester, ни новые runtime packages не требуются.
Runtime-кандидат — C# 5/.NET; Python не является частью будущего WFP helper.
В build helper явно указаны известные locations SDK/MSVC, не пути/порты хоста
для policy. На другом компьютере выбирать установленный toolchain явно;
автоматической установки или fallback на другую ABI нет.

Из корня проекта, выбрав **новое** имя попытки:

```powershell
python -B reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/tools/build_test.py attempt06
```

Это компилирует 3 managed libraries + managed offline executable и выполняет
C++ `/Zs` static assertions **без link/run C++ приложения**. Затем запускается
только `OfflineTests.exe selftest ...`. Все outputs и дочерние TEMP/TMP — в
новой TASK-local attempt directory. Не повторять успешные прогоны без изменения
source, finding или нового проверочного условия.

Чтобы доказать чувствительность readback regression, отдельный mutant build:

```powershell
python -B reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/tools/build_test.py mutant_port05
```

Ожидается ровно один FAIL: `readback_rejects_wrong_port_even_same_owner_digest`.
Helper сохраняет этот красный результат и признаёт контролируемый mutant killed,
а не объявляет mutant security PASS. **Mutant binaries никогда не использовать
как продукт.** Финальная действительная сборка — `evidence/attempt05/`.

Не запускать `NativePreview` через reflection/собственный host. Не менять
Execution Policy, не использовать Bypass/Unblock/elevation. Для реальных Windows
операций отсутствуют разрешение, trusted authority и лабораторные доказательства.

## Чего этот пакет не доказывает

62/62 managed tests, 22 C++ assertions и корректная сборка не подтверждают
фильтрацию Windows. Native preview не вызывался; port takeover, ALE descriptor
matching, поддержка NOT_EQUAL на выбранных layers, arbitration, existing flows,
BFE/boot, DNS/delegation, children и реальный upstream остаются открытыми.
Полный factual result, исходные результаты и сохранность — `report.md`,
`checks_final.json`, `manifest.json`.
