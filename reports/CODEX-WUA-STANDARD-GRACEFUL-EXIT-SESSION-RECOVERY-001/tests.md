# OFFLINE проверки, 17.11.2026

Все проверки выполнялись через проектный `.venv`, изолированные временные Workspace и HTTP loopback. GigaChat OAuth/catalog/inference: **0/0/0**. Реальные пользовательские записи не открывались для записи.

| Проверка | Итог | Evidence |
|---|---|---|
| Runtime, live-control, STANDARD, launcher, shutdown | **73/73 PASS** | `evidence/runtime_final.txt` |
| Соседние server, Ordinary, EVM, Ultra Chat, Turn HTTP, Tk cleanup | **53 PASS, 1 SKIP / 54** | `evidence/adjacent_python.txt` |
| Shutdown negatives, duplicate, stop → port free → restart | **3/3 PASS** | `evidence/shutdown_final.txt` |
| EVM + Ultra Chat JS | **127/127 PASS** | `evidence/js_final.txt` |
| S1 route/reconciliation | **69/69 PASS**, isolation/evidence 0 | `evidence/s1_final.txt` |
| S2 policy guard | **73/73 PASS**, isolation 0 | `evidence/s2_final.txt` |
| Python compile | **6 файлов PASS** | `evidence/compile.txt` |

Отрицательные случаи: живой owner lock отвергает второй grant; legacy `ACTIVE` без lock-признака не переписывается; неправильный Origin, отсутствие write-token и неверное подтверждение не запускают shutdown; после STOPPING новые запросы получают 503; два одновременных shutdown получают идемпотентный 202; старая сессия не может пройти `check()` после recovery. Recovery сохраняет прежний grant `ACTIVE` как evidence и не делает provider POST.

Промежуточные FAIL сохранены: `evidence/runtime_initial.txt` содержал два устаревших ожидания кодов тестов и Mock без tracker; `evidence/js_initial.txt` — ожидание старой общей надписи; `evidence/s1_initial.txt` и `evidence/s2_initial.txt` — старые точные AST pins после разрешённых изменений. Исправлены тестовые ожидания/launcher Mock compatibility и обновлены только точные pins. Первое случайное выполнение системным Python 3.13 не имело `httpx`; повторено на проектном `.venv` и не считается проверкой кода.

**Не проверено:** реальный legacy account, настоящий API, paid Turn, все состояния in-flight Turn при аварийном завершении, другие процессы STANDARD/TEST, физический браузер и системный крестик. Авторские PASS не являются независимой приёмкой.
