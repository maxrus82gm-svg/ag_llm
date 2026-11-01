# Матрица API и доказательств

Статусы: **OBSERVED** — реальный HTTP результат; **DOC ONLY** — актуальная публичная документация, не испытание установленной версии; **NOT RUN** — не вызывалось; **NOT VERIFIED** — нельзя подтвердить. Ошибка discovery не равна UNSUPPORTED. Никаких POST/DELETE, inference, load/unload или model management в этой TASK не выполнялось.

| Метод / свойство | Ollama .9:11434 | Colibri / .77:8000 | Вывод для адаптера |
| --- | --- | --- | --- |
| GET /api/version | OBSERVED 200, 0.40.13 | NOT RUN: это не подтверждённый маршрут Colibri | Версия сервера отдельно от версии adapter/protocol |
| GET /api/tags | OBSERVED 200, один installed deepseek-r1:8b | NOT RUN / identity unknown | Native discovery сохраняет digest/size/details и provenance |
| GET /api/ps | OBSERVED 200, models=[] | NOT VERIFIED | installed ≠ loaded; не прогревать автоматически |
| GET /v1/models | OBSERVED 200, тот же ID | На .77 timeout; на локальном :8000 RemoteDisconnected | Подтверждён только listing shape у Ollama; chat compatibility из него не следует |
| GET /health | Не вызывался, /api/version уже отвечает | .77 timeout, локальный :8000 disconnect | Не навязывать всем движкам одну health URL |
| GET /openapi.json | Не вызывался | .77 timeout, локальный :8000 disconnect | Нет server schema evidence; маршруты Colibri неизвестны |
| POST /api/chat | DOC ONLY / NOT RUN | NOT VERIFIED | Native chat model/messages; отдельный capability gate |
| POST /api/generate | DOC ONLY / NOT RUN | NOT VERIFIED | Native prompt interface, не молчаливая замена chat |
| POST /v1/chat/completions | DOC ONLY / NOT RUN | Только гипотеза из TASK; NOT VERIFIED | Частичная совместимость проверяется по конкретным полям/модели |
| POST /v1/completions | DOC ONLY / NOT RUN | NOT VERIFIED | Не смешивать prompt и messages API |
| Stream | Native NDJSON описан документацией; NOT RUN | NOT VERIFIED | Раздельные parser profiles для native NDJSON и OpenAI-style SSE; фактический SSE installed-version NOT RUN |
| Cancel | NOT RUN; backend cancellation semantics не установлены | NOT VERIFIED | Закрытие клиента не доказывает остановку вычисления/отсутствие результата |
| Load/unload/keep_alive | DOC ONLY, не исполнялись | NOT VERIFIED | Это операции управления ресурсом, не discovery |
| Usage / timing | Документированы prompt_eval_count/eval_count и durations; NOT RUN | NOT VERIFIED | Сохранять provider raw; не выдумывать token usage или цену из отсутствия полей |
| Error / busy / timeout | Установленный inference API не испытывался на ошибки; клиентские disconnect/timeout наблюдались на :8000 | Timeout/disconnect; HTTP 401/404/429/503 не наблюдались | Разделять transport failure, HTTP error и mid-stream error |
| Queue / parallelism | Реальные параметры сервера неизвестны | NOT VERIFIED | Никакой нагрузки ради определения capacity; admission limits задавать отдельно |
| Auth / bind | Анонимные inventory GET приняты на loopback; auth других методов NOT VERIFIED | NOT VERIFIED; локальный listener :: принадлежит Manager.exe | Нельзя считать все методы анонимными либо сервис безопасным по одному GET |
| Tools / reasoning / images / JSON schema | tags advertises tools/thinking/completion; выполнение NOT RUN, images/schema не подтверждены | NOT VERIFIED | Capabilities по tuple connection/model/revision и method, с источником/датой |

## Источники публичного контракта

Ollama прямо описывает **подмножество** OpenAI API; совпадение /v1/models не доказывает полную совместимость payload, streaming, ошибок, usage или tools. Для установленной 0.40.13 проверены только GET выше. [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility).

Native /api/chat и /api/generate имеют разные входные формы; документация описывает model/messages либо prompt, опции и счётчики ответа. Поддержка конкретных параметров установленным сервером и выбранной моделью остаётся NOT RUN. [Chat](https://docs.ollama.com/api/chat), [Generate](https://docs.ollama.com/api/generate).

Документация native streaming описывает NDJSON и отключение через stream=false. Mid-stream error может прийти после начала HTTP 200, поэтому завершение HTTP не должно автоматически означать успешную генерацию. [Streaming](https://docs.ollama.com/api/streaming), [Errors](https://docs.ollama.com/api/errors).

FAQ описывает настройку bind, keep_alive, загрузку/выгрузку и зависимость параллелизма от памяти. Эти возможности здесь не проверялись и не применялись. [Ollama FAQ](https://docs.ollama.com/faq).

Техническое первичное описание установленного Colibri вне Git/GitHub не получено. Результаты поиска сторонних обзоров/зеркал не использовались как доказательство; запрет Git/GitHub через зеркала не обходился. Не приписывать неизвестной установке общий backend Ollama или поведение JustVugg/colibri.
