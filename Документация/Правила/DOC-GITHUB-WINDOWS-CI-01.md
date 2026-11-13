# DOC-GITHUB-WINDOWS-CI-01 — GitHub-hosted Windows: независимые тесты для агентов

**Статус:** ACTIVE / USER GO 13.11.2026. **Проект:** ag_llm / Web Alarm Ultra.  
**Читать:** при постановке независимой проверки Python/JS/HTTP/OFFLINE, при создании или изменении GitHub Actions workflow и при приёмке авторского отчёта.  
**Ответственный:** ChatGPT-координатор / независимый проверяющий. Локальные Codex/Claude не получают новых Git/GitHub прав.  
**Связанные правила:** №08 «Старт», №18 «Регламент», DOC-COMMIT-01, DOC-GITHUB-HANDOFF-01, №20 §5а.  
**Границы:** не разрешает REAL, OAuth, paid, эксплуатационный deploy, изменения STANDARD/Tkinter или закрытие непроверенных safety-gates.

## 1. Главный принцип

**Воспроизводимые независимые программные проверки по умолчанию исполняются на GitHub Actions с windows-latest, а не на машине пользователя.** Цель — экономия вызовов Desktop Commander, независимый компьютер, прозрачная фиксация SHA/лога и повторяемый результат.

Маршрут: опубликованная сдача Codex/Claude в main → сверка исходников и отчетов → отдельный workflow в GPT → GitHub-hosted Windows → guard + тесты → logs/artifacts/run ID → независимый verdict → только после PASS полная документальная приёмка → один атомарный номерной GPT commit → пользовательский merge в main.

**Desktop Commander — исключение**, допустимое лишь для действительно физической проверки: реальный GUI/клики/F5, запуск пользовательского CMD/ярлыка, устройство/драйвер, конкретный компьютер, недоступное на CI локальное железо или иное подтверждённое ограничение. Перед его использованием назвать причину, минимальный объем и почему GitHub Actions не подходит. Не пользоваться им для git clone, обычного pytest, unit-тестов и чтения исходников.

Авторские тесты исполнителя и собственный независимый GitHub CI — разные доказательства. Чужие числа PASS никогда не превращаются в «independent» от чтения отчёта.

## 2. Подготовить проверяемую базу

1. Получить TASK ID, HISTORY ID, путь report/manifest/evidence, последний пользовательский source commit в main. Прочитать нужные файлы и diff, проверить source SHA, реальную публикацию.
2. Сравнить main и GPT; убедиться, что новая проверка будет на нужном коде. Не затирать чужие изменения и не force-push. Следующий номер commit брать только после чтения DOC-COMMIT-01 и проверки свежих HEAD/истории.
3. Составить матрицу: feature/negative tests, safety S1/S2/S3a, adjacent regression, UI-Node, browser/GUI NOT RUN, real-provider NOT RUN. Для каждой группы указать штатный *entrypoint*, expected tests/exit, требуемые данные, допустимую сеть, варианты failure.
4. Провести **dependency closure** тестов: перечислить весь runtime import graph, сторонние python-пакеты, JavaScript, вызываемые дочерними Python-процессами скрипты, JSON fixtures, guard, синтетические datasets, RAW и любые read-only artifacts. Исходники могут быть в repo, а исторические RAW могут отсутствовать.
5. Выбрать уже существующий guard/runner. Для H32: reports/CODEX-WUA-CHAT-S3B-ORDINARY-FAKE-ADMISSION-001/run_checks.py; для S1/S2 — их standalone runners, а не обычное pytest discovery. **Не подменять тесты самодельными PASS-заглушками**.

Выполнение только на exact source tree/commit. В логе записать полный git rev-parse HEAD, Python/Node versions, список реально запущенных селекторов и результаты. Run на GPT, включающей исходный main, может содержать workflow/документы сверх source commit: исходный SHA и diff обязательно сравнить.

## 3. Как запускается Windows на GitHub

Создать YAML в .github/workflows/ с конкретным непересекающимся именем и набором тестов. Обязательный фрагмент:

- runs-on: windows-latest; timeout-minutes конечен.
- permissions: contents: read; actions/checkout с persist-credentials: false.
- actions/setup-python с указанной версией, для AST/pin-sensitive тестов использовать проверенную Python 3.12.x; при расхождении patch version фиксировать его в evidence.
- Никаких GitHub secrets, реального GigaChat credentials, DNS/внешней сети или пользовательского Workspace при выполнении тестов.
- Сеть для установки тестовых зависимостей в setup **не равна разрешению реальной сети в тестируемом runtime**. В runtime действует строгий pre-import guard.
- workflow_dispatch можно добавить для ручного запуска в интерфейсе GitHub, но если используемый коннектор не умеет запускать dispatch, workflow обязан автоматически запускаться через push в GPT. Действительно запустить означает получить run ID, а не только написать YAML.
- workflow не должен требовать Desktop Commander, включать credentials checkout или менять main.

Пример шаблона ниже **адаптировать под TASK**. Путь TASK-REPORT и тестовые имена — placeholders, их нельзя оставлять неизменёнными. Runner должен запускаться внутри изоляции с pre-import guard, а не обычным pytest без границ.

~~~yaml
name: TASK independent OFFLINE Windows
on:
  push:
    branches: [GPT]
    paths:
      - .github/workflows/gpt-task-independent.yml
  workflow_dispatch:
permissions:
  contents: read
jobs:
  independent-offline:
    runs-on: windows-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
          sparse-checkout: |
            /*.py
            /*.js
            /*.json
            /web_alarm/
            /reports/TASK-REPORT/
            /reports/OTHER-TEST-DEPENDENCY/
            /.github/workflows/gpt-task-independent.yml
          sparse-checkout-cone-mode: false
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Prepare isolated Windows test interpreter
        shell: pwsh
        run: |
          $ErrorActionPreference = 'Stop'
          python -m venv .venv
          if ($LASTEXITCODE -ne 0) { throw 'venv failed' }
          & .\.venv\Scripts\python.exe -m pip install --no-input --disable-pip-version-check 'pytest==9.1.1' 'httpx==0.28.1' 'mcp==2.2.0'
          if ($LASTEXITCODE -ne 0) { throw 'pip failed' }
          New-Item -ItemType Directory ci-evidence -Force | Out-Null
          git rev-parse HEAD | Set-Content ci-evidence/source-sha.txt
          & .\.venv\Scripts\python.exe --version
      - name: Real guarded runner; fail if absent
        shell: pwsh
        run: |
          $ErrorActionPreference = 'Stop'
          $target = 'reports/TASK-REPORT/run_checks.py'
          if (-not (Test-Path $target)) { throw 'Runner absent from checkout' }
          # For H32 run_checks.py expects its own per-stage evidence in TASK-REPORT/evidence.
          # Replace the stage and test selector with the approved task-specific ones.
          & .\.venv\Scripts\python.exe -B -X utf8 $target ci_review test_web_alarm_ordinary_admission.py > ci-evidence/test.log 2>&1
          $rc = $LASTEXITCODE
          Get-Content ci-evidence/test.log
          if ($rc -ne 0) { throw "Tests failed: $rc" }
          $proof = 'reports/TASK-REPORT/evidence/ci_review.result.json'
          if (-not (Test-Path $proof)) { throw 'Structured result absent' }
          Copy-Item $proof ci-evidence/result.json
          $result = Get-Content ci-evidence/result.json -Raw | ConvertFrom-Json
          if ($result.exit_code -ne 0 -or $result.unexpected_guard_denials -ne 0 -or
              $result.counts.'test:passed' -lt 1) { throw 'Inadequate result' }
      - name: Stage failure evidence
        if: always()
        shell: pwsh
        run: |
          New-Item -ItemType Directory ci-evidence -Force | Out-Null
          $source = 'reports/TASK-REPORT/evidence'
          foreach ($ext in @('.result.json','.cases.json','.guard.jsonl','.stdout.txt','.stderr.txt')) {
            $file = Join-Path $source ("ci_review"+$ext)
            if (Test-Path $file) { Copy-Item $file ci-evidence -Force }
          }
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: task-independent-windows
          path: ci-evidence/
          if-no-files-found: warn
          retention-days: 14
~~~

**Важно:** приведённый шаблон — каркас, не свидетельство запуска. Перед публикацией заменить placeholders, воспроизвести actual dependencies и конкретный ожидаемый count (число >0 — недостаточный финальный gate). Для отключённой/недоступной isolation допускается только FAIL/NOT RUN, не обход. Полный рабочий пример текущего проекта: .github/workflows/gpt-web28-h32-independent.yml. Ещё один проверенный ориентир: .github/workflows/gpt-web29-h31-f01-independent.yml.

## 4. Windows-specific ограничения и решения

### 4.1. Checkout и длинные пути

В ag_llm имеются глубоко вложенные исторические reports/runs/mirror. Полный checkout на Windows может завершиться **Filename too long** до запуска Python. Проверка H32 GitHub run 43393073446 показала именно этот bootstrap failure.

**Правильный подход:** sparse-checkout с указанием реально необходимых Python/JS/JSON-модулей, web_alarm и точных reports/fixtures/guard. Обычное сокращение списка без пересчёта дочерних зависимостей приводит к ложному RED «файл test-helper отсутствует». Проверка H32 run 43393490540: первый недостающий nested dependency reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/run_checks.py, 5 FAIL внутри suite при наличии 231 PASS; это CI packaging gap, не доказательство регрессии продукта. Добавить именно зависимость и повторить тот же тест. Нельзя изменять продуктивный код для устранения отсутствующего checkout-файла.

Не расширять sparse-checkout на длинные архивы только ради формальности; если тесту действительно нужны архивные RAW — отдельно решать доступность и пределы Windows пути, не обходя integrity gates.

### 4.2. MAX_PATH в синтетическом хранилище

В глубоком GitHub runner TEMP и Test Run Store может встретиться длинный путь, даже когда source checkout уже прошёл. Ставить временные синтетические пути коротко (например C:\h32\la), проверив уникальность scratch и возможность удаления без затрагивания чужих данных. Для дочерних Python процессов передавать TEMP, TMP, TMPDIR, LOCALAPPDATA и при необходимости APPDATA. Не менять реальные хранилища пользователя. Проблемы пути сначала воспроизводить с теми же тестами в другом коротком TEMP, не ослаблять assertions.

### 4.3. Артефакты на разных дисках

GitHub-hosted Windows может размещать рабочий каталог на D:, а synthetic TEMP на C:. actions/upload-artifact@v4 не обязан строить общий корень для перечня путей с разных томов. Надёжный способ: отдельный этап if: always(), скопировать результаты из обоих мест в одну папку **на одном томе**, например в рабочем ci-evidence или runner.temp, затем загрузить одну папку. Так была исправлена инфраструктурная ошибка H30, не продуктовый код.

### 4.4. PowerShell/exit codes

PowerShell не гарантирует падения шага на любом ненулевом коде native exe. После каждого Python/Node запуска немедленно сохранять $LASTEXITCODE, печатать stdout/stderr и делать throw/exit на nonzero. Числа тестов, FAIL/ERROR/SKIP, отрицательные контроли и guard violations проверять структурно, а не по слову PASS в консоли.

### 4.5. Дочерние процессы и import isolation

Некоторые тесты вызывают вложенный Python-скрипт внутри reports. Все такие paths должны присутствовать в sparse checkout, Python в .venv должен существовать и соответствовать version pin, а guard должен наследоваться ребёнком через проверяемые env/PYTHONPATH. Не импортировать runtime до guard. Если программа запрещает любой subprocess, использовать только approved специально изолированный runner; не отключать guard ради зелёного цвета.

## 5. Исторические RAW и честные границы

S1 (test_rt002_s1_routes.py) закреплён на **исторических RAW** в .ultra/audit/..., с pinned SHA/длиной. Эти данные не обязаны быть в GitHub. Если их нет в GitHub-hosted sandbox, отметка: **S1 INDEPENDENT = NOT RUN / REQUIRED RAW UNAVAILABLE**. Никакой synthetic substitute, чужой SHA или пропуск проверки не может превратить это в 69 independent PASS.

S2 core (test_rt002_s2_budget_policy.py) содержит встроенный derived dataset, поэтому без параметра --provenance может быть independently tested на CI. S2 --provenance отдельно требует исторический RAW: без него provenance = NOT RUN. Обычное pytest discovery для S1/S2 может породить SKIP, и это **не** PASS этих standalone gates.

Если нужный тест требует реальный browser/CMD/F5, которого не было на CI, честная запись: **GUI PHYSICAL NOT RUN**. GitHub-hosted Windows Python/Node тесты не доказывают физический пользовательский smoke.

## 6. Обязательная OFFLINE-защита

- Реальные ключи, OAuth, paid, external provider: **запрещены** в независимом OFFLINE CI. Удалять/не передавать GIGACHAT_* и реальные provider credentials, не печатать секреты.
- Использовать проверенный pre-import sitecustomize/guard, блокирующий внешнюю сеть/DNS и чтение/запись вне синтетических разрешённых областей. Разрешение loopback возможно только для явно проверяемых HTTP smoke, без любой внешней сети.
- Проверять, что guard действительно установлен, а попытка нарушения выявляется отрицательными контролями. Для тестов, намеренно вызывающих connect/DNS/credential, ожидаемые отказанные пробы считать отдельно от **неожиданных** нарушений. Требование: unexpected guard events = 0.
- Снимок тестового root, имена Workspace/Chat, fake responses, Model и бюджеты — synthetic. Никакого доступа к существующим пользовательским Workspace, ORIGINAL Audit, Tkinter Standard, секретам или Git credentials.
- Не использовать «REAL transport под fake флагом». При UNKNOWN сохранять небезопасность повторной отправки, а не запускать живой провайдер.

## 7. Как независимый агент читает результат

Обязательное evidence:
- исходные branch, source SHA, CI workflow SHA, UTC timestamp, точные команды, Python/Node versions;
- GitHub Actions run ID, job ID, run URL и status/conclusion;
- факт подготовки guarded sandbox, отрицательные guard controls и denied/expected/unexpected totals;
- run artifact (ZIP link/ID), stdout, stderr, структурные cases/result JSON, checksum при возможности;
- тестовые counts без суммирования перекрывающихся прогонов; fail/error/skip/NOT RUN отдельно;
- полная матрица ожиданий против результата и точная область independent PASS;
- конкретные ограничения: физический GUI, historical RAW, full S3b, REAL/OAuth/paid и прочее неисполненное.

На **completed SUCCESS** ориентироваться можно лишь после просмотра job steps и содержимого evidence: сам успех workflow не доказывает все заявленные gates. На failed workflow сначала найти точный failed step и классифицировать:
1) checkout/deps/artifact infrastructure;
2) missing test fixture/sparse closure;
3) guard/isolated environment defect;
4) настоящий тестовый FAIL продукта;
5) недоступное необходимое evidence;
6) runner-only compatibility difference.

Исправлять причины адресно, сохранять URL исходного failed run и результат повторного run. Не переименовывать его в PASS и не скрывать отрицательную историю. Не заявлять завершение H32, полного S3b или готовность GigaChat LIVE по partial CI.

## 8. GitHub-only схема для координатора

1. Через доступный GitHub connector/read-only API сверить main, GPT, diff, исходные файлы, отчет/manifest/evidence.
2. Подготовить конкретную проверку и YAML по разделам выше, readback содержимого. Публиковать **только в GPT**, с соблюдением DOC-COMMIT-01 и согласованной атомарной логической единицы; пользователь делает merge. Локальным Codex/Claude не передавать GitHub-ключи.
3. При push workflow с path trigger запускается автоматически; получить run ID из GitHub Actions. Если workflow не запущен — это NOT RUN, независимо от наличия файла в репозитории. Если connector не умеет workflow_dispatch, push trigger обязателен.
4. Читать jobs/steps/logs и artifacts через GitHub. Для процесса «RUNNING» не писать PASS заранее.
5. После PASS, а не до него, оформить independent review и нужные документы задачи в одном атомарном closeout коммите; при FAIL/PARTIAL честно вести OPEN и отдельный remedy. Инфраструктурный CI repair с собственным подтверждённым scope документировать отдельно и не выдавать за закрытие задачи.
6. Считать синхронизацию пользователя только после его собственного merge/pull; локальный ПК не становится актуальным автоматически.

**Готовый короткий checklist перед ответом пользователю:** GitHub run существует? HEAD и source SHA совпадают? Test count и guards проверены? Artifact доступен? Исторические недоступные gates помечены NOT RUN? Браузер не приписан unit-тесту? Нет REAL/OAuth? В №05 сохранены OPEN? В GPT один утверждённый пакет и нет незаявленного merge?

## 9. Фактические ссылки проекта

- H30 успешный CI после исправления staging: https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43287825151
- H31 независимый Windows CI F-01: https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43264689001
- H32 первый CI с full checkout MAX_PATH: https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43393073446
- H32 sparse checkout и пробел дочернего S3a helper: https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43393490540
- Живой шаблон H32: .github/workflows/gpt-web28-h32-independent.yml
- Правило обязательной документальной приёмки: Документация/18_Регламент сопровождения документации.md

**Обновление этого правила:** если новый сбой CI повторяется или меняется контракт GitHub Actions, сначала собрать exact log/URL и доказать причину; менять руководство по подтверждённым фактам, не по догадке.
