# Запрос отдельного AMENDMENT — S2 isolation oracle после появления OFFLINE S3a

Текущая TASK исправляет исключительно S1. S2 и production не редактировались.

Финальный точный guarded S2 core selector выполнил 73 tests:
**72 PASS / 1 FAIL, 0 ERROR/SKIP, isolation violations=0, exit1**.
FAIL: `IsolationTests.test_no_production_module_imports_the_policy_yet`.

Предикат перебирает s1._production_modules() и запрещает импорт
ultra_budget_policy любым module кроме самого policy. В этом наборе уже есть
созданный в H23 OFFLINE ultra_budget_ledger.py, который намеренно импортирует S2
policy. Оба файла присутствуют в before baseline текущей TASK и остались
byte-identical. Тело _production_modules тоже не менялось. Следовательно,
source-level причина не зависит от изменения S1 inventory. Отдельный S2 baseline
до текущих правок не исполнялся; не выдавать этот анализ за такой прогон.

Сохранены `evidence/s2.*` и `s2_preexisting_failure_analysis.json`.
Промежуточный S2 прогон имел ещё FAIL route_registry из-за расширения экспортного
EXPECTED_SEND_SITES; это исправлено в пределах S1 сохранением его прежних восьми
утверждённых routes и сравнением полного набора 12 в EXPECTED_PRODUCTION_SITES.
`s2_intermediate.*` оставлен. Финальная route_registry проверка PASS.

**STOP:** изменение S2 oracle вне WRITE scope текущей TASK не выполняется.
Запрашивается отдельный узкий AMENDMENT/TASK: READ S2/S3a и production import
closure; WRITE test_rt002_s2_budget_policy.py и новый evidence package для
различения OFFLINE dependency library и production enforcement. Потребуются
негативные тесты, сохраняющие запрет реального production подключения policy
без S3b, полный guarded S2 core и нужные S1/S3a regressions.

Не разрешены policy/runtime/route изменения, исключение ledger из S1 scanner,
широкий allowlist по имени, real providers, Git/GitHub. Это запрос, не GO и не
назначение следующей задачи.
