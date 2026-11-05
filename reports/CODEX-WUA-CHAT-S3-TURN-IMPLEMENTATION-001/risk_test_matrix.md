# Change / risk / independent oracle

| Изменение / риск | Проверка | Oracle |
| --- | --- | --- |
| Приём, ключ, другой текст / дубли | TurnTests roundtrip/conflict/distinct keys; TurnHttpTests two clients | Ровно два RAW для одного Turn, один start/result, одинаковые IDs/bytes при replay |
| Crash до/после RAW | raw_crash; process_exit с exit 71/72/73/74 | Реальный код выхода, прежние ID/bytes, фиксированные SUCCEEDED или UNKNOWN, без нового исполнения |
| Потерянный HTTP response | lost_physical_http_reply | Реальное отсутствие ответа, RemoteDisconnected, затем прежний result, два RUN events |
| ACK после fsync потерян | result_fsync_lost_ack | Настоящий pending Run Store, recover сохраняет result, imitate.call_count=1 |
| GET / read authority | get_never_starts; read_requires_read_authority | GET не вызывает имитатор и не меняет files; write token не читающий и наоборот |
| Два writers | two_service_writers, two_processes_one_turn, two HTTP clients | Shared disk: один start/result, два RAW; reaped child exit0 |
| Отмена до старта / late result | service cancellation; HTTP cancellation с Event barrier | CANCELLED до старта; UNKNOWN после; поздний ответ не создаёт assistant RAW |
| Повреждение RAW/event | corrupt_raw_or_event, damaged_ready_raw | 503 до новых записей; snapshot совпадает; execution не вызывается |
| Повреждённая проекция READY | stale_ready_projection | Сохранён RED: imitate вызван повторно; после исправления snapshot неизменен, imitate не вызван |
| Неверные refs/root/scope/Unicode | invalid_references, foreign_chat, HTTP negatives | 400/403/404/409, исходные bytes неизменны |
| Junction audit-path | native Windows service case + original prerequisite oracle | Внешний synthetic marker единственный и неизменный |
| Browser retry/double click/reload | 3 S3 Node VM tests | Один POST, сохранённый key, нет текста/token в localStorage; reload восстанавливает GET |
| UI happy path | Реальный IAB: click и Enter, reload; screenshot/AX | Видны введённое сообщение, фиксированный TEST ответ и та же история |
| Старый RAW / пользовательские данные | preexisting_raw; conservation receipts | Точные bytes + filenames/sizes/SHA на baseline, без live write |
| Physical provider/Git calls | guard before imports; source review TurnService | Fixed constant function, отсутствует transport dispatch; 0 forbidden attempts в receipts |
| Predecessor/core compatibility | Original 3 prerequisites; Run Store/audit 62; Python171; JS161 | Реальные runner exits/counts и raw output; SKIP остаются явными |

Test limits: не все Windows symlink privileges доступны (5 existing SKIP). Node VM не заменяет браузер; browser happy path не заменяет отрицательные HTTP/core tests. Guard разрешает loopback fixtures, не является OS firewall; `os._exit` не выдаёт atexit receipt. Power loss, full Ultra/Git-dependent discovery, native Tk/picker GUI, portability и реальные providers NOT RUN. Shared-core final TOCTOU и прежние staging/picker OPEN не объявлены закрытыми.
