# Sing-box и V2Ray Core: решение ещё не принято

|Критерий|A — отдельный sing-box-кандидат|B — выделенный V2Ray Core|
|---|---|---|
|Что действительно есть|Exact binary/hash; embedded sing-box v1.13.4/revision claim, нынешний child v2rayN|Точного разрешённого binary/release path нет; полный диск не обследовался|
|Source/schema доверие|BLOCKED; требуется matching authentic local bundle|BLOCKED; сначала выбрать exact release и bundle|
|CONNECT/strict routing/default/fallback|UNVERIFIED|UNVERIFIED|
|Изменение работающего экземпляра|Не требуется и запрещено; будущий B экземпляр должен быть независимым|Не требуется и запрещено; будущий B экземпляр тоже независим|
|Текущий contract|family=V2Ray несовместим; смена требует user decision и отдельного scoped schema/config mapping review|Family intent согласуется по имени, но binary/config compatibility не доказана|
|Native config schema|Синтаксис/semantics не проверены; автоматически переводить нельзя|Синтаксис/semantics конкретной версии неизвестны; не выдумывать|
|Listener и egress ownership|Обязательно один B-owned процесс; нынешний пользовательский child этого не доказывает|То же требование; имя V2Ray само его не обеспечивает|
|Дополнительные сетевые каналы|Нужен полный source audit; compiled tags указывают на разнообразие компонентов, не на активность|Нужен аналогичный versioned source audit, никаких предположений о «более безопасном» engine|
|Переносимость|Не переносить текущие путь/SID/port/config/secrets; нужны versioned supply/config/Windows gates|Те же требования; дополнительно нет уже идентифицированной local supply|
|Оставшаяся работа|Provenance→source/schema review→явный engine decision→минимальное согласованное изменение contract→OS lab proofs|Exact release/supply selection→тот же review→native config mapping→OS lab proofs|

**Рекомендация:** сначала адресно получить source/provenance bundle уже идентифицированного sing-box v1.13.4. Это сокращает неопределённость и не требует скачивания/запуска нового core. Высокая уверенность в таком порядке исследования; **недостаточная уверенность для выбора operational engine**. Существующие данные не доказывают, что V2Ray Core нужен для F2 или что sing-box уже удовлетворяет строгой архитектуре.

F2 решается фактическим владением listener/egress одним B process, проверенной конфигурацией и системной политикой, а не заменой названия продукта. Ни одно направление автоматически не получает GO. Полный broker stack/NPFS переписывать не требуется; изменения family/schema допустимы только после решения пользователя и source review. Точный следующий выбор — `next_user_decision.md`.
