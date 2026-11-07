# Source excerpts at formal closeout
Exact source hashes and immutable byte snapshots: source_state_before_closeout.json. Line numbers below are one-based.

## web_alarm/ui.py:340
```text
340: <div id="chatTurnControls" hidden><p id="chatTurnStatus" role="status" aria-live="polite"></p><button type="button" id="chatTurnCheck" title="Если ответ не появился или связь прервалась, проверьте состояние отправленного запроса.">Проверить состояние запроса</button> <button type="button" id="chatTurnCancel">Отменить</button> <button type="button" id="chatTurnNew" hidden>Новый отдельный запрос</button></div>
```

## web_alarm/ui.py:1912
```text
1912: function turnScope(){return chat.workspace&&chat.chat?'webAlarm.testTurn.'+chat.workspace+'.'+chat.chat:null}
1913: function turnPending(){try{return JSON.parse(localStorage.getItem(turnScope())||'null')}catch(_){return null}}
1914: function turnBase(){return '/ultra/chat/workspaces/'+encodeURIComponent(chat.workspace)+'/chats/'+encodeURIComponent(chat.chat)+'/turns'}
1915: function renderTurnComposer(){
1916:   const enabled=chatTurn.available&&!!chat.workspace&&!!chat.chat;
1917:   const pending=turnPending();
1918:   $('chatInput').disabled=!enabled||chatTurn.busy;$('chatSend').disabled=!enabled||chatTurn.busy;
1919:   $('chatTurnControls').hidden=!enabled;
1920:   $('chatTurnCancel').disabled=!enabled||!pending||(stage5Offline&&!!chatTurn.state&&!['READY','ATTEMPTING'].includes(chatTurn.state));
1921:   $('chatModelPick').disabled=stage5Offline?!chatTurn.models.length:chatTurn.available;
1922:   if(stage5Offline){
1923:     const selected=chatTurn.models.find(m=>m.model_id===chatTurn.model);
1924:     $('chatInput').readOnly=typeof pending?.text==='string';
1925:     $('chatSend').disabled=!enabled||chatTurn.busy||!selected;
1926:     $('chatInput').placeholder='Сообщение TEST-имитатору';
1927:     $('chatTurnNew').disabled=chatTurn.busy;
1928:     text('chatComposerNote',pending?'TEST · повтор использует сохранённый ключ и модель исходного запроса.':'TEST · локальный имитатор. Enter — отправить, Shift+Enter — новая строка.');
1929:     text('chatModel',selected?'TEST · '+selected.display_name:'TEST · выберите модель');
1930:     text('chatModelPick',(selected?.display_name||'Выбрать модель')+' ▾');
1931:     text('chatSidebarNote','TEST · история хранится общим ядром Ultra.');
1932:   }
1933:   else if(chatTurn.available){text('chatComposerNote','TEST · локальный имитатор. Выбранная модель не вызывается. Enter — отправить, Shift+Enter — новая строка.');$('chatInput').placeholder='Сообщение TEST-имитатору';text('chatModel','TEST · локальный имитатор');text('chatModelPick','TEST · без LLM');text('chatSidebarNote','TEST: ответы создаёт локальный имитатор. История хранится общим ядром Ultra.')}
1934:   else{text('chatComposerNote','Отправка сообщений появится на следующем этапе. Сейчас Ultra Chat читает сохранённую историю, создаёт и переименовывает диалоги.')}
1935:   $('chatSend').textContent=turnPending()?'Повторить / восстановить':'Отправить';
1936: }
1937: function showTurn(result){
1938:   if(!result||result.mode!==(stage5Offline?'TEST_OFFLINE':'TEST')||typeof result.turn_id!=='string'||!['ACCEPTING','READY','ATTEMPTING','SUCCEEDED','FAILED','CANCELLED','UNKNOWN'].includes(result.state))throw Error('Некорректный Turn');
1939:   chatTurn.revision++;
1940:   chatTurn.state=result.state;
1941:   const labels={ACCEPTING:'Приём не завершён. Для продолжения нужен исходный текст.',READY:'Принято. Ожидает явного продолжения.',ATTEMPTING:'Имитатор выполняет запрос…',SUCCEEDED:'TEST: ответ сохранён.',FAILED:'TEST: выполнение завершилось ошибкой.',CANCELLED:'Отменено до выполнения.',UNKNOWN:'Исход неизвестен. Повтор ключа проверит сохранённые факты; повторного исполнения нет.'};
1942:   const detail=stage5Offline?' · '+result.references.model_ref+(result.usage?.total_tokens==null?'':' · usage '+result.usage.total_tokens):'';
1943:   text('chatTurnStatus',labels[result.state]+detail);
1944:   $('chatTurnNew').hidden=result.state!=='UNKNOWN';
1945:   $('chatTurnCancel').disabled=!['READY','ATTEMPTING'].includes(result.state);
1946:   if(['SUCCEEDED','FAILED','CANCELLED'].includes(result.state)){
1947:     const hadPending=!!turnPending();
1948:     localStorage.removeItem(turnScope());
1949:     if(stage5Offline?hadPending:result.state==='SUCCEEDED')$('chatInput').value=''
1950:   }
1951:   renderTurnComposer();
1952: }
1953: async function checkTurn(){
1954:   renderTurnComposer();let pending=turnPending();if(!chatTurn.available||!turnScope()||(!pending&&!stage5Offline))return;
1955:   const epoch=chat.epoch,revision=chatTurn.revision;
1956:   try{
1957:     const found=pending?{turn:await chatGet(turnBase()+'/by-key/'+encodeURIComponent(pending.key))}:await chatGet(turnBase()+'/latest');
1958:     if(epoch!==chat.epoch||revision!==chatTurn.revision||!found.turn)return;
1959:     const result=found.turn;
1960:     if(stage5Offline&&!pending&&!['SUCCEEDED','FAILED','CANCELLED'].includes(result.state)){
1961:       if(chatTurn.dismissed.get(turnScope())===result.idempotency_key)return;
1962:       pending={key:result.idempotency_key,model:result.references.model_ref,text:found.text};
1963:       localStorage.setItem(turnScope(),JSON.stringify(pending));
1964:     }
1965:     if(stage5Offline&&typeof pending?.text==='string')$('chatInput').value=pending.text;
1966:     showTurn(result);await loadChatHistory(false)
1967:   }
1968:   catch(e){if(epoch===chat.epoch)text('chatTurnStatus',e.httpStatus===404?'Запрос ещё не найден. Повторите исходный текст с сохранённым ключом.':'Не удалось проверить состояние запроса. Ключ сохранён, автоматического повтора нет.')}
```

## web_alarm/ui.py:1970
```text
1970: async function sendTurn(){
1971:   if(!chatTurn.available||chatTurn.busy||!chat.workspace||!chat.chat||!$('chatInput').value.trim()||(stage5Offline&&!chatTurn.model))return;
1972:   const epoch=chat.epoch,scope=turnScope(),base=turnBase(),value=$('chatInput').value;
1973:   chatTurn.busy=true;renderTurnComposer();text('chatTurnStatus','Принимаем TEST-запрос…');
1974:   try{
1975:     let pending=JSON.parse(localStorage.getItem(scope)||'null');
1976:     if(!pending){
1977:       pending=stage5Offline?{key:crypto.randomUUID(),text:value,model:chatTurn.model}:{key:crypto.randomUUID()};
1978:       localStorage.setItem(scope,JSON.stringify(pending));
1979:       if(stage5Offline){chatTurn.state=null;$('chatTurnNew').hidden=true;renderTurnComposer()}
1980:     }
1981:     else{
1982:       try{
1983:         const previous=await chatGet(base+'/by-key/'+encodeURIComponent(pending.key));
1984:         if(['SUCCEEDED','FAILED','CANCELLED','ATTEMPTING'].includes(previous.state)){
1985:           if(epoch===chat.epoch){showTurn(previous);await loadChatHistory(false)}return
1986:         }
1987:       }catch(e){if(e.code!=='turn_not_found'&&e.code!=='turn_acceptance_incomplete')throw e}
1988:     }
1989:     const request=stage5Offline?{idempotency_key:pending.key,text:pending.text??value,model_ref:pending.model}:
1990:       {idempotency_key:pending.key,text:value,model_ref:'local-test:v1',context_ref:'empty:v1',config_ref:'test-only:v1'};
1991:     const result=await chatPost(base,request);
1992:     if(epoch===chat.epoch){showTurn(result);await loadChatHistory(false)}
1993:   }catch(e){
1994:     const invalid=stage5Offline&&['invalid_turn_request','invalid_offline_request','request_too_large'].includes(e.code);
1995:     if(invalid)localStorage.removeItem(scope);
1996:     if(epoch===chat.epoch)text('chatTurnStatus',invalid?'TEST · исправьте текст или выбор модели.':
1997:       e.code==='idempotency_conflict'?'Конфликт ключа: верните исходный текст. Перезаписи нет.':'Ответ не подтверждён. Ключ сохранён. Проверьте состояние запроса перед повтором.')
1998:   }
1999:   finally{chatTurn.busy=false;renderTurnComposer()}
2000: }
2001: async function cancelTurn(){
2002:   const pending=turnPending();if(!pending)return;const epoch=chat.epoch;
2003:   try{const current=await chatGet(turnBase()+'/by-key/'+encodeURIComponent(pending.key));const result=await chatPost(turnBase()+'/'+current.turn_id+'/cancel',{});if(epoch===chat.epoch)showTurn(result)}
2004:   catch(_){if(epoch===chat.epoch)text('chatTurnStatus','Отмена не подтверждена. Проверьте состояние запроса.')}
2005: }
2006: const CHAT_REASON={missing_history:'В папке нет истории Ultra',missing_path:'Папка недоступна',not_directory:'Путь не является папкой',invalid_metadata:'Данные Ultra повреждены',unsupported_version:'Данные Ultra более новой версии',unsafe_storage_link:'Внутри хранилища Ultra ссылка вместо папки или файла — чтение запрещено',unreadable:'Данные не читаются',unsupported_registration_id:'Эта регистрация не поддерживается Ultra Chat',registry_unavailable:'Реестр Workspace недоступен',too_many_workspaces:'Слишком много Workspace',chats_listing_too_large:'Слишком много диалогов для просмотра',history_too_large:'История слишком большая для просмотра',foreign_identity:'Диалог принадлежит другому Workspace',chat_damaged:'Диалог повреждён',ultra_core_unavailable:'Общее ядро Ultra недоступно'};
2007: const CHAT_OUTCOME={failed:['Ошибка выполнения (старая запись), не ответ модели','bad'],no_answer:['Ответ не сохранён','warn'],interrupted:['Прервано · исход неизвестен','unknown'],unknown:['Исход неизвестен','unknown']};
```

## web_alarm/ui.py:2226
```text
2226:   try{
2227:     const data=await chatGet('/ultra/chat/workspaces');
2228:     if(epoch!==chat.epoch)return;
2229:     if(!validChatWorkspaces(data))throw Error('Некорректный ответ сервера о Workspace');
2230:     text('chatAccess',chatTurn.available?'TEST · локальный имитатор · без LLM':'Данные проверяет сервер · сообщения не отправляются');chat.workspaces=data.workspaces;
2231:     text('chatWorkspaceState',data.state!=='ok'?chatReason(data.reason):data.workspaces.length?'':'Нет зарегистрированных Workspace. Нажмите «+ Создать Workspace».');
2232:     if(chat.workspace&&!chat.workspaces.some(w=>w.wa_workspace_id===chat.workspace)){chat.workspace=null;chat.expanded=null;chat.chat=null;chat.chats=[];renderChatList();clearChatHistory('Выберите диалог')}
2233:     const selected=chat.workspaces.find(w=>w.wa_workspace_id===chat.workspace);
2234:     text('chatWorkspaceName',selected?selected.display_name:'Ultra Chat');
2235:     renderChatWorkspaces();
2236:     if(chat.workspace){await loadChatList();return true}
2237:     const first=chat.workspaces.find(w=>w.history==='ok');
2238:     if(first)await selectChatWorkspace(first.wa_workspace_id);
2239:     return true
2240:   }catch(e){if(epoch===chat.epoch){text('chatWorkspaceState','Список Workspace не загружен');chatFailure(e)}return false}
2241: }
2242: function selectChatWorkspace(id){
2243:   if(chat.renamingWorkspace?.busy)return Promise.resolve();
2244:   closeWorkspaceName();
2245:   if(chat.workspace===id){chat.expanded=chat.expanded===id?null:id;renderChatWorkspaces();return Promise.resolve()}
2246:   closeChatName();
2247:   $('chatNameForm').hidden=true;// a pending save of the old Workspace must not expose its editor in the new one
2248:   chat.epoch++;chat.workspace=id;chat.expanded=id;chat.chat=null;chat.chats=[];chat.messages=[];chat.page=null;chat.olderBusy=false;
2249:   const w=chat.workspaces.find(item=>item.wa_workspace_id===id);text('chatWorkspaceName',w?w.display_name:'Ultra Chat');
2250:   renderChatWorkspaces();renderChatList();clearChatHistory('Выберите диалог');
2251:   return loadChatList()
2252: }
2253: async function loadChatList(){
2254:   if(!chat.workspace)return;
2255:   const epoch=chat.epoch;text('chatListState','Загружаем диалоги…');
2256:   try{
2257:     const data=await chatGet('/ultra/chat/workspaces/'+encodeURIComponent(chat.workspace)+'/chats');
2258:     if(epoch!==chat.epoch)return;
2259:     if(!validChatList(data))throw Error('Некорректный ответ сервера о диалогах');
2260:     notice('chatError','');chat.chats=data.chats;const hidden=chatCount(data.excluded);
2261:     text('chatListState',data.state!=='ok'?chatReason(data.reason):(data.chats.length?'Диалогов: '+data.chats.length:'В этом Workspace нет сохранённых диалогов.')+(hidden?' · не показано посторонних записей: '+hidden:''));
2262:     if(chat.chat&&!chat.chats.some(c=>c.chat_id===chat.chat&&c.status==='ok')){chat.chat=null;clearChatHistory('Выберите диалог')}
2263:     renderChatList();
2264:     if(chat.chat)return loadChatHistory(false);
2265:     const newest=chat.chats.filter(c=>c.status==='ok').at(-1);// the list is in creation order: open the newest dialogue
2266:     if(newest)return selectChat(newest.chat_id)
2267:   }catch(e){if(epoch===chat.epoch){text('chatListState','Список диалогов не загружен');chatFailure(e)}}
2268: }
2269: function selectChat(id){
2270:   if(chatEdit.mode==='rename'&&chatEdit.chatId!==id)closeChatName();
2271:   chat.epoch++;chat.chat=id;chat.messages=[];chat.page=null;chat.olderBusy=false;
2272:   renderChatList();clearChatHistory('Загружаем историю…');renderTurnComposer();return loadChatHistory(false).then(()=>checkTurn())
2273: }
2274: async function loadChatHistory(older){
2275:   if(!chat.workspace||!chat.chat||(older&&(chat.olderBusy||!chat.page?.next_before)))return;
2276:   const epoch=chat.epoch;
2277:   let path='/ultra/chat/workspaces/'+encodeURIComponent(chat.workspace)+'/chats/'+encodeURIComponent(chat.chat)+'/messages?limit='+CHAT_PAGE;
2278:   if(older){path+='&before='+encodeURIComponent(chat.page.next_before);chat.olderBusy=true;$('chatOlder').disabled=true}
2279:   try{
2280:     const data=await chatGet(path);
2281:     if(epoch!==chat.epoch)return;
2282:     if(!validChatHistory(data))throw Error('Некорректный ответ сервера об истории диалога');
2283:     notice('chatError','');chat.messages=older?[...data.messages,...chat.messages]:data.messages;chat.page=data.page;
2284:     renderChatHistory(data,older)
2285:   }catch(e){if(epoch===chat.epoch)chatFailure(e)}
2286:   finally{if(older&&epoch===chat.epoch){chat.olderBusy=false;$('chatOlder').disabled=false}}
2287: }
2288: function startChat(){if(chat.started)return;chat.started=true;loadChatModel();return loadChatWorkspaces()}
```

## web_alarm/ultra_chat.py:340
```text
340:     def messages(self, wa_workspace_id: str, chat_id: str, before: str | None, limit: int) -> dict[str, Any]:
341:         core = _core()
342:         record = self._registration(wa_workspace_id)
343:         base = {"wa_workspace_id": wa_workspace_id, "chat_id": chat_id}
344:         try:
345:             history = core.read_chat_history_bounded(record.workspace_root, chat_id)
346:         except core.StorageReadError as exc:
347:             if exc.code == "chat_not_found":
348:                 raise UltraChatError(404, "chat_not_found", "Chat is not found in this Workspace") from None
349:             state = "too_large" if exc.code == "history_too_large" else "unavailable"
350:             return {**base, "history_state": state, "reason": exc.code, "messages": [], "excluded": {},
351:                     "excluded_ids": [], "page": {"limit": limit, "returned": 0, "has_more": False, "next_before": None}}
352:         runs, tasks, classification = _run_index(core, record.workspace_root)
353:         messages = _classify(history["messages"], runs, tasks)
354:         page = _page(messages, before, limit)
355:         if history["excluded"]:
356:             state = "partial"
357:         elif not history["messages"]:
358:             state = "empty"
359:         else:
360:             state = "complete"
361:         return {**base, "chat": history["chat"], "history_state": state, "excluded": history["excluded"],
362:                 "excluded_ids": history["excluded_ids"], "total_messages": len(messages),
363:                 "outcome_source": classification, **page}
```

## web_alarm/ultra_chat.py:448
```text
448:     def messages(self, wa_workspace_id, chat_id, before, limit):
449:         page = super().messages(wa_workspace_id, chat_id, before, limit)
450:         assistants = [item for item in page["messages"] if item["role"] == "assistant"]
451:         if not assistants:
452:             return page
453:         core = _core()
454:         root, workspace_id = self._writable_workspace(core, wa_workspace_id)
455:         turns = self._turns_for(root, workspace_id, chat_id)
456:         try:
457:             for item in assistants:
458:                 raw = core.read_ultra_json_bounded(root, ("chats", chat_id, "messages", item["message_id"] + ".json"),
459:                                                   max_bytes=32768)
460:                 run_id = raw["producer"]["run_id"]
461:                 turn = turns.get(root, workspace_id, chat_id, run_id)
462:                 if (turn["mode"] != "TEST_OFFLINE" or turn["state"] != "SUCCEEDED"
463:                         or turn["assistant_message_id"] != item["message_id"] or turn["answer"] != item["text"]):
464:                     raise ValueError("TEST assistant RAW has no confirmed result")
465:         except (KeyError, TypeError, ValueError, core.StorageReadError, UltraChatError):
466:             raise UltraChatError(503, "offline_history_invalid", "TEST answer could not be verified") from None
```

## web_alarm/ultra_chat.py:505
```text
505:     def _turns_for(self, root, workspace_id, chat_id):
506:         with self._owner_lock:
507:             owner = self._owners.get((workspace_id, chat_id))
508:         return owner[1] if owner else self._fixture_turns(root)
509: 
510:     def _turn_request(self, action, wa_workspace_id, chat_id, value, body=None):
511:         if action == "submit":
512:             return self.submit_turn(wa_workspace_id, chat_id, value)
513:         root, workspace_id = self._writable_workspace(_core(), wa_workspace_id)
514:         turns = self._turns_for(root, workspace_id, chat_id)
515:         if action == "cancel":
516:             return turns.cancel(root, workspace_id, chat_id, value, body)
517:         if action == "lookup":
518:             return turns.lookup(root, workspace_id, chat_id, value)
519:         return turns.get(root, workspace_id, chat_id, value)
520: 
521:     def _context(self, root, workspace_id, chat_id, turns):
522:         """Project one bounded, verified completed pair from this Chat only."""
523:         from provider_accounting import canonical_json_text
524:         core = _core()
525:         try:
526:             history = core.read_chat_history_bounded(root, chat_id)
527:         except core.StorageReadError as error:
528:             raise UltraChatError(503, "offline_history_invalid", "TEST context could not be read") from error
529:         if history["excluded"]:
530:             raise UltraChatError(503, "offline_history_invalid", "TEST history contains damaged records")
531:         context = [{"role": "system", "content": "TEST offline chat " + chat_id}]
532:         messages = history["messages"]
533:         for assistant in reversed(messages):
534:             producer = assistant.get("producer", {})
535:             if assistant["role"] != "assistant" or producer.get("kind") != "offline_chat_fixture":
536:                 continue
537:             turn = turns.get(root, workspace_id, chat_id, producer.get("run_id"))
538:             user = next((m for m in messages if m["message_id"] == turn["user_message_id"]), None)
539:             if (turn["state"] != "SUCCEEDED" or assistant["message_id"] != turn["assistant_message_id"]
540:                     or not user or user["role"] != "user"):
541:                 raise UltraChatError(503, "offline_history_invalid", "TEST pair is not backed by its Turn")
542:             if all(len(canonical_json_text(m["text"]).encode("utf-8")) <= 1024 for m in (user, assistant)):
543:                 context.extend({"role": m["role"], "content": m["text"]} for m in (user, assistant))
544:             break
545:         return context
```

## web_alarm/ultra_chat.py:599
```text
599:     def latest_turn(self, wa_workspace_id, chat_id):
600:         import run_store
601:         from .turn_service import TURN
602:         core = _core()
603:         root, workspace_id = self._writable_workspace(core, wa_workspace_id)
604:         try:
605:             index = run_store.load_workspace_run_index(root)
606:             entries = [(entry["display_id"], run_id) for run_id, entry in index["runs"].items()
607:                        if entry.get("chat_id") == chat_id and TURN.fullmatch(run_id)]
608:             if not entries:
609:                 return {"turn": None, "text": None}
610:             _, run_id = max(entries, key=lambda item: int(item[0].split("-")[-1]))
611:             turns = self._turns_for(root, workspace_id, chat_id)
612:             turn = turns.get(root, workspace_id, chat_id, run_id)
613:             text = None
614:             if turn["state"] != "ACCEPTING":
615:                 raw = core.read_ultra_json_bounded(root, ("chats", chat_id, "messages", turn["user_message_id"] + ".json"),
616:                                                   max_bytes=32768)
617:                 text = raw["original_text"]
618:             return {"turn": turn, "text": text}
619:         except UltraChatError as error:
620:             if error.code == "turn_acceptance_incomplete":
621:                 return {"turn": None, "text": None}
622:             raise
623:         except (OSError, ValueError, KeyError, core.StorageReadError):
624:             raise UltraChatError(503, "turn_storage_unavailable", "TEST Turn could not be read") from None
625: 
626: 
627: # Safe text for every refusal of the shared writer; the core's own message (which may name a path) is never sent.
628: _WRITE_REFUSALS = {
629:     "title_changed": (409, "The chat was renamed elsewhere meanwhile"),
```

## web_alarm/ultra_chat.py:706
```text
706: def _classify(messages: list[dict[str, Any]], runs: Mapping, tasks: Mapping) -> list[dict[str, Any]]:
707:     """Outcome of each message for display only (contract section 4); RAW is never rewritten."""
708:     answered = {m.get("task_block_id") for m in messages if m["role"] == "assistant" and m.get("task_block_id")}
709:     result = []
710:     for message in messages:
711:         item = {key: message[key] for key in ("message_id", "role", "created_at", "text")}
712:         block = message.get("task_block_id")
713:         task = tasks.get(block) if block else None
714:         block_statuses = [_status_of(runs.get(run_id)) for run_id in task.get("runs", [])] if isinstance(task, dict) \
715:             and isinstance(task.get("runs"), list) else []
716:         block_statuses = [status for status in block_statuses if status]
717:         producer = message.get("producer") or {}
718:         if message["role"] == "assistant":
719:             own = _status_of(runs.get(producer.get("run_id"))) if producer.get("run_id") else None
720:             statuses = [own] if own else block_statuses
721:             if message["text"].startswith(LEGACY_FAILURE_PREFIX) or "FAILED" in statuses:
722:                 item["outcome"] = "failed"
723:             elif statuses and all(status == "RUNNING" for status in statuses):
724:                 item["outcome"] = "unknown"
725:             elif statuses:
726:                 item["outcome"] = "completed"
727:             else:
728:                 item["outcome"] = "legacy"
729:             if statuses:
730:                 item["run_status"] = statuses[-1]
731:             if producer.get("model_display_name"):
732:                 item["model"] = producer["model_display_name"]
733:         elif message["role"] == "user":
734:             if block and block not in answered:
735:                 item["outcome"] = "interrupted" if block_statuses and all(
736:                     status == "RUNNING" for status in block_statuses) else "no_answer"
737:             else:
738:                 item["outcome"] = "request"
739:         else:
740:             item["outcome"] = "service"
741:         result.append(item)
```

## web_alarm/turn_service.py:160
```text
160:     @staticmethod
161:     def _run_status(state):
162:         return 'COMPLETED' if state == 'SUCCEEDED' else state if state in {'FAILED', 'CANCELLED', 'UNKNOWN'} else 'RUNNING'
163: 
164:     @staticmethod
165:     def _save(root, turn):
166:         runs.update_run_summary_index(root, turn['run_id'],
167:                                       {'turn': turn, 'run_status': TurnService._run_status(turn['state'])})
168: 
169:     @staticmethod
```

## web_alarm/turn_service.py:195
```text
195:     def _commit(root, turn, role, text):
196:         core.commit_raw_message(root, turn['chat_id'], turn[role+'_message_id'], role, text,
197:             expected_workspace_id=turn['workspace_id'], task_block_id=turn['task_block_id'],
198:             producer=TurnService._producer(turn))
```

## web_alarm/turn_service.py:320
```text
320:         if state == 'SUCCEEDED':
321:             answer = terminal[1]['answer'] if offline else ANSWER
322:             if (turn['cancel_requested'] or (not offline and self._result(root,turn) is None)
323:                     or self._raw(root,turn,'assistant').get('original_text') != answer):
324:                 raise ValueError('Success not backed by result and RAW')
325:         if state == 'ATTEMPTING' and not self._is_active(root, turn): state = 'UNKNOWN'
326:         view = {**{k:turn[k] for k in ('turn_id','run_id','attempt_id','user_message_id','assistant_message_id','idempotency_key')},
327:                 'state':state,'cancel_requested':turn['cancel_requested'],'references':dict(turn['references']),
328:                 'answer':answer,'mode':'TEST'}
329:         if offline:
330:             discarded = next((r['payload'] for r in records if r['event'] == 'turn_result_discarded'), None)
331:             view.update(mode='TEST_OFFLINE', request_ref=turn['prepared']['request_ref'],
332:                         usage=terminal[1]['usage'] if terminal else discarded['usage'] if discarded else None)
333:         return view
334: 
335:     def _settle_offline(self, root, turn):
336:         records = self._records(root, turn)
337:         view = self._view(root, turn, records=records)
338:         if turn['state'] == 'ATTEMPTING' and not turn['cancel_requested']:
339:             terminal = self._offline_evidence(turn, records)
340:             if terminal:
341:                 state, payload = terminal
342:                 if state == 'SUCCEEDED':
343:                     self._commit(root, turn, 'assistant', payload['answer'])
344:                 turn['state'] = state
345:                 self._save(root, turn)
346:                 saved = self._load(root, turn['workspace_id'], turn['chat_id'], turn['turn_id'])
347:                 return self._view(root, saved)
348:         return view
349: 
350:     def _is_active(self, root, turn):
351:         with self._active_lock: return (str(Path(root).resolve()),turn['turn_id']) in self._active
352: 
353:     def get(self, root, workspace_id, chat_id, turn_id):
354:         with self._session(root, workspace_id, chat_id):
355:             return self._view(root, self._load(root,workspace_id,chat_id,turn_id))
356: 
357:     def lookup(self, root, workspace_id, chat_id, key):
358:         if not isinstance(key,str) or not KEY.fullmatch(key):
359:             raise UltraChatError(400,'invalid_turn_request','Invalid retry key')
360:         return self.get(root,workspace_id,chat_id,identities(workspace_id,chat_id,key)['turn_id'])
361: 
```

## web_alarm/turn_service.py:393
```text
393:             # This explicit repeat may repair an interrupted append, never execute a started attempt again.
394:             runs.recover_run_records(root,turn['run_id'])
395:             if turn['state'] == 'ACCEPTING':
396:                 if offline:
397:                     self._view(root, turn)
398:                 self._commit(root,turn,'user',body['text'])
399:                 turn['state']='READY'; self._save(root,turn)
400:             if turn['state'] == 'ATTEMPTING':
401:                 if offline:
402:                     return self._settle_offline(root, turn)
403:                 if not turn['cancel_requested'] and self._result(root,turn):
404:                     self._commit(root,turn,'assistant',ANSWER)
405:                     turn['state']='SUCCEEDED'; self._save(root,turn)
406:                 return self._view(root,turn)
407:             if turn['state'] != 'READY': return self._view(root,turn)
408:         return self._execute(root,workspace_id,chat_id,ids['turn_id'])
409: 
```

## web_alarm/turn_service.py:470
```text
470:                 if result.request_ref != prepared.request_ref or result.model != prepared.model:
471:                     raise ValueError('Offline adapter result identity mismatch')
472:                 outcome, execution, answer = result.outcome.value, result.execution.value, result.text
473:                 usage = asdict(result.usage)
474:             self._check_usage(usage)
475:             if turn['cancel_requested']:
476:                 event, payload = 'turn_result_discarded', {**start, 'usage': usage}
477:                 self._offline_evidence(turn, [*records, {'event': event, 'payload': payload}])
478:                 self._event(root, turn, event, payload)
479:                 return self._view(root, turn)
480:             if turn['state'] != 'ATTEMPTING':
481:                 raise ValueError('Offline attempt no longer owns the Turn')
482:             mapped = OFFLINE_OUTCOMES.get((outcome, execution))
483:             if mapped is None:
484:                 raise ValueError('Unexpected offline adapter outcome')
485:             event = mapped[0]
486:             payload = {**start, 'outcome': outcome, 'execution': execution, 'answer': answer, 'usage': usage}
487:             self._offline_evidence(turn, [*records, {'event': event, 'payload': payload}])
488:             self._event(root, turn, event, payload)
489:             return self._settle_offline(root, turn)
490: 
491:     def cancel(self, root, workspace_id, chat_id, turn_id, body):
492:         if body != {}: raise UltraChatError(400,'invalid_turn_request','Cancellation body must be empty')
493:         with self._session(root,workspace_id,chat_id):
494:             turn=self._load(root,workspace_id,chat_id,turn_id)
495:             if turn['state'] in {'SUCCEEDED','FAILED','CANCELLED','UNKNOWN'}: return self._view(root,turn)
496:             runs.recover_run_records(root,turn['run_id'])
497:             offline = turn['schema_version'] == 2
498:             if offline:
499:                 view = self._settle_offline(root, turn)
500:                 if turn['state'] in {'SUCCEEDED', 'FAILED', 'UNKNOWN'}:
501:                     return view
502:             turn['cancel_requested']=True
503:             # ACCEPTING has no confirmed user RAW; retain the unaccepted state rather than forge acceptance.
504:             if turn['state']=='ACCEPTING':
505:                 raise UltraChatError(409,'turn_acceptance_incomplete','Complete acceptance before cancellation')
506:             turn['state']='UNKNOWN' if turn['state']=='ATTEMPTING' else 'CANCELLED'
507:             self._save(root,turn)
508:             self._event(root,turn,'turn_cancel_requested',self._started(turn) if offline else {'attempt_id':turn['attempt_id']})
509:             return self._view(root,turn)
```

## context_storage.py:1652
```text
1652: def read_chat_history_bounded(
1653:     workspace_root: str | Path,
1654:     chat_id: str,
1655:     *,
1656:     limits: ReadLimits = DEFAULT_READ_LIMITS,
1657: ) -> dict[str, Any]:
1658:     """All valid RAW messages of one chat in display order, with counted exclusions, under hard I/O limits.
1659: 
1660:     The listing is refused above ``max_message_files`` entries and the whole history above ``max_history_bytes``;
1661:     a single file above ``max_message_bytes`` is excluded unread. Reading stops at the byte budget even if files
1662:     grow after they were listed. For display only: the model context keeps its own fail-closed path.
1663:     """
```

## context_storage.py:1730
```text
1730:         except StorageReadError as exc:
1731:             if exc.code == "too_large" and cap < limits.max_message_bytes:
1732:                 raise StorageReadError("history_too_large") from None
1733:             if exc.code != "missing":
1734:                 exclude(exc.code if exc.code in {"too_large", "unsafe_storage_link"} else "damaged", message_id)
1735:             continue
1736:         budget -= len(data)
1737:         try:
1738:             record = _decode_json(data)
1739:         except StorageReadError:
1740:             exclude("damaged", message_id)
1741:             continue
1742:         reason = _message_problem(record, message_id, chat_id, workspace_id)
1743:         if reason is None and message_id in seen:
1744:             reason = "duplicate_id"
1745:         if reason:
1746:             exclude(reason, message_id)
1747:             continue
1748:         seen.add(message_id)
1749:         item: dict[str, Any] = {"message_id": message_id, "role": record["role"],
1750:                                 "created_at": record["created_at"], "text": record["original_text"]}
1751:         if "task_block_id" in record:
1752:             item["task_block_id"] = record["task_block_id"]
1753:         producer = record.get("producer")
1754:         if isinstance(producer, dict):
1755:             item["producer"] = {key: producer[key] for key in ("kind", "run_id", "model_id", "model_display_name")
1756:                                 if isinstance(producer.get(key), str)}
1757:         messages.append(item)
1758:     messages.sort(key=lambda item: (item["created_at"], item["message_id"]))
1759:     return {**identity, "chat": chat, "messages": messages, "excluded": excluded, "excluded_ids": excluded_ids,
1760:             "files_read": len(candidates), "bytes_read": limits.max_history_bytes - budget}
1761: 
1762: 
1763: def _storage_parts(relative_parts: tuple[str, ...]) -> tuple[str, ...]:
1764:     if not relative_parts or any(
1765:         not isinstance(part, str) or not _STORAGE_NAME_RE.fullmatch(part) or part in {".", ".."}
```

## reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/review_fixture.py:38
```text
38: 
39:         api = WebAlarmApi(root / "registry")
40:         chat = OfflineUltraChatService(api.registry, root)
41:         server = create_server(api, port=0, offline_chat=chat)
42:         server.daemon_threads = False
43:         worker = threading.Thread(target=server.serve_forever)
44:         worker.start()
45:         url = f"http://127.0.0.1:{server.server_address[1]}/"
46:         print(f"TEST OFFLINE · {url}", flush=True)
47:         original = _FixtureTransport.send
48: 
49:         async def visible_attempt(fake, payload, **kwargs):
50:             await asyncio.sleep(1.5)
51:             return await original(fake, payload, **kwargs)
52: 
53:         try:
54:             if args.web_smoke or args.web:
```
