"""TEST Turns. Identity/projection in the existing RUN summary, events in Run Store, RAW in Ultra.

The explicit S4B fixture uses the same writer and lifecycle. A lost owner is UNKNOWN;
only an already durable result can be published on an explicit repeat of the same request.
"""
from __future__ import annotations

import contextlib
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import tempfile
import threading
import time

import context_storage as core
import run_store as runs
from .ultra_chat import UltraChatError

REFERENCES = {'model_ref': 'local-test:v1', 'context_ref': 'empty:v1', 'config_ref': 'test-only:v1'}
ANSWER = 'TEST: сообщение принято.'
OFFLINE_REF = 's4b-offline:v1'
OFFLINE_OUTCOMES = {
    ('completed', 'response_received'): ('turn_result', 'SUCCEEDED'),
    ('invalid_response', 'response_received'): ('turn_failed', 'FAILED'),
    ('rejected', 'not_started'): ('turn_failed', 'FAILED'),
    ('transport_error', 'may_have_executed'): ('turn_uncertain', 'UNKNOWN'),
    ('unknown_after_start', 'may_have_executed'): ('turn_uncertain', 'UNKNOWN'),
    ('unknown_after_start', 'response_received'): ('turn_uncertain', 'UNKNOWN'),
}
KEY = re.compile(r'^[A-Za-z0-9_-]{16,128}$')
TURN = re.compile(r'^turn_[0-9a-f]{64}$')
STATES = {'ACCEPTING', 'READY', 'ATTEMPTING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'UNKNOWN'}


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def identities(workspace_id, chat_id, key):
    token = _digest([workspace_id, chat_id, key])
    return dict(turn_id='turn_'+token, run_id='turn_'+token, task_block_id='tb_'+token[:32],
                user_message_id='msg_'+_digest([token, 'user'])[:32],
                assistant_message_id='msg_'+_digest([token, 'assistant'])[:32], attempt_id='attempt_'+token)


class TurnService:
    def __init__(self, *, test_roots=(), offline_adapter=None):
        self.test_roots = frozenset(Path(p).resolve() for p in test_roots)
        if offline_adapter is not None:
            from .ordinary_chat_test_adapter import OfflineTestAdapter
            temp_root = Path(tempfile.gettempdir()).resolve()
            if (type(offline_adapter) is not OfflineTestAdapter or not self.test_roots
                    or any(temp_root not in p.parents for p in self.test_roots)):
                raise ValueError('Offline adapter requires explicit temporary Workspace roots')
        self._offline_adapter = offline_adapter
        self._active = set()
        self._active_lock = threading.Lock()

    def capability(self):
        return {'available': bool(self.test_roots), 'mode': 'TEST' if self.test_roots else 'DISABLED',
                'references': dict(REFERENCES), 'label': 'TEST · локальный имитатор · без LLM'}

    def _require_test(self, root):
        # Explicit synthetic root allowlist; registration by itself grants no TEST execution permission.
        if Path(root).resolve() not in self.test_roots:
            raise UltraChatError(403, 'test_turn_unavailable', 'TEST sending is disabled for this Workspace')

    @contextlib.contextmanager
    def _session(self, root, workspace_id, chat_id):
        self._require_test(root)
        try:
            with core._existing_workspace_writer(root, workspace_id) as writer:
                core._require_chat_for_write(writer, chat_id)
                yield
        except UltraChatError:
            raise
        except core.ChatNotFoundError:
            raise UltraChatError(404, 'chat_not_found', 'Chat is not in this Workspace') from None
        except (OSError, ValueError, core.StorageWriteError, core.StorageReadError):
            raise UltraChatError(503, 'turn_storage_unavailable', 'Turn could not be verified or stored') from None

    def _body(self, body):
        try:
            text_size = len(body['text'].encode('utf-8')) if isinstance(body,dict) and isinstance(body.get('text'),str) else 0
        except UnicodeError:
            raise UltraChatError(400,'invalid_turn_request','Text must be valid Unicode') from None
        if (not isinstance(body, dict) or set(body) != {'idempotency_key', 'text', *REFERENCES}
                or not isinstance(body['idempotency_key'], str) or not KEY.fullmatch(body['idempotency_key'])
                or not isinstance(body['text'], str) or not body['text'].strip()
                or text_size > 2048):
            raise UltraChatError(400, 'invalid_turn_request', 'Expected a small message and a stable retry key')
        if body['config_ref'] == OFFLINE_REF and self._offline_adapter is not None:
            if any(type(body[k]) is not str or not body[k].strip() or len(body[k]) > 256
                   for k in ('model_ref', 'context_ref')):
                raise UltraChatError(400, 'invalid_turn_reference', 'Invalid offline reference')
        elif any(body[k] != v for k, v in REFERENCES.items()):
            raise UltraChatError(409, 'invalid_turn_reference', 'Only the explicit TEST references are allowed')
        return copy.deepcopy(body)

    def _load(self, root, workspace_id, chat_id, turn_id):
        if not isinstance(turn_id, str) or not TURN.fullmatch(turn_id):
            raise UltraChatError(400, 'invalid_turn_id', 'Invalid Turn ID')
        summary = runs.load_run_summary(root, turn_id, chat_id)
        if summary is None:
            raise UltraChatError(404, 'turn_not_found', 'Turn is not in this Chat')
        if not isinstance(summary, dict):
            raise ValueError('Damaged RUN summary')
        turn = summary.get('turn')
        if turn is None:
            raise UltraChatError(409, 'turn_acceptance_incomplete', 'Repeat the original request to finish acceptance')
        if (not isinstance(turn, dict) or type(turn.get('schema_version')) is not int
                or turn['schema_version'] not in (1, 2)
                or summary.get('workspace_id') != workspace_id or turn.get('workspace_id') != workspace_id
                or turn.get('chat_id') != chat_id or not isinstance(turn.get('state'), str)
                or turn['state'] not in STATES
                or not isinstance(turn.get('idempotency_key'), str) or not KEY.fullmatch(turn['idempotency_key'])
                or not isinstance(turn.get('request_sha256'), str) or not re.fullmatch('[0-9a-f]{64}',turn['request_sha256'])
                or any(turn.get(k) != v for k, v in identities(workspace_id,chat_id,turn['idempotency_key']).items())
                or turn.get('turn_id') != turn_id or type(turn.get('cancel_requested')) is not bool):
            raise ValueError('Damaged Turn binding')
        if turn['schema_version'] == 1:
            if turn.get('references') != REFERENCES:
                raise ValueError('Damaged TEST references')
        else:
            self._verify_offline_binding(root, summary, turn)
        return turn

    @staticmethod
    def _binding(turn):
        return _digest({k: v for k, v in turn.items()
                        if k not in {'state', 'cancel_requested', 'binding_sha256'}})

    def _verify_offline_binding(self, root, summary, turn):
        if self._offline_adapter is None:
            raise UltraChatError(403, 'test_turn_unavailable', 'Offline Turn adapter is disabled')
        refs, snapshot = turn.get('references'), turn.get('prepared')
        if (type(refs) is not dict or set(refs) != set(REFERENCES)
                or refs['config_ref'] != OFFLINE_REF
                or any(type(refs[k]) is not str or not refs[k].strip() or len(refs[k]) > 256
                       for k in ('model_ref', 'context_ref'))
                or type(snapshot) is not dict
                or set(snapshot) != {'model', 'context', 'limits', 'request_ref'}
                or type(snapshot['model']) is not dict
                or snapshot['model'].get('model_id') != refs['model_ref']
                or not isinstance(snapshot['request_ref'], str)
                or not re.fullmatch('sha256:[0-9a-f]{64}', snapshot['request_ref'])
                or turn.get('binding_sha256') != self._binding(turn)):
            raise ValueError('Damaged offline request binding')
        entry = runs.get_run_index_entry(root, turn['run_id'])
        for key in ('run_id', 'chat_id', 'task_block_id'):
            if summary.get(key) != turn[key] or not entry or entry.get(key) != turn[key]:
                raise ValueError('Damaged offline RUN identity')
        if summary.get('run_status') != self._run_status(turn['state']):
            raise ValueError('Damaged offline RUN status')

    @staticmethod
    def _run_status(state):
        return 'COMPLETED' if state == 'SUCCEEDED' else state if state in {'FAILED', 'CANCELLED', 'UNKNOWN'} else 'RUNNING'

    @staticmethod
    def _save(root, turn):
        runs.update_run_summary_index(root, turn['run_id'],
                                      {'turn': turn, 'run_status': TurnService._run_status(turn['state'])})

    @staticmethod
    def _event(root, turn, event, payload):
        return runs.append_run_record(root, turn['run_id'], source='SERVER', event=event,
                                      payload=payload, timestamp=time.time())

    @staticmethod
    def _producer(turn):
        if turn['schema_version'] == 2:
            return {'kind': 'offline_chat_fixture', 'run_id': turn['run_id'], 'turn_id': turn['turn_id'],
                    'model_id': turn['references']['model_ref'], 'model_display_name': 'TEST · S4A offline',
                    'request_ref': turn['prepared']['request_ref'], 'binding_sha256': turn['binding_sha256']}
        return {'kind': 'test_imitation', 'run_id': turn['run_id'], 'turn_id': turn['turn_id'],
                'model_display_name': 'TEST · локальный имитатор'}

    @staticmethod
    def _raw(root, turn, role):
        message_id = turn[role+'_message_id']
        value = core.read_ultra_json_bounded(root, ('chats', turn['chat_id'], 'messages', message_id+'.json'), max_bytes=32768)
        if (not isinstance(value, dict) or value.get('workspace_id') != turn['workspace_id'] or value.get('chat_id') != turn['chat_id']
                or value.get('message_id') != message_id or value.get('role') != ('user' if role == 'user' else 'assistant')
                or value.get('producer') != TurnService._producer(turn) or value.get('task_block_id') != turn['task_block_id']
                or (turn['schema_version'] == 2 and value.get('schema_version') != core.SCHEMA_VERSION)):
            raise ValueError('RAW identity mismatch')
        return value

    @staticmethod
    def _commit(root, turn, role, text):
        core.commit_raw_message(root, turn['chat_id'], turn[role+'_message_id'], role, text,
            expected_workspace_id=turn['workspace_id'], task_block_id=turn['task_block_id'],
            producer=TurnService._producer(turn))

    def _records(self, root, turn):
        return runs.load_stream_records(root, turn['run_id'], 'SERVER')

    def _result(self, root, turn):
        results = [r for r in self._records(root, turn) if r['event'] == 'turn_result']
        if not results: return None
        if len(results) != 1 or results[0]['payload'] != {'attempt_id':turn['attempt_id'],'answer':ANSWER}:
            raise ValueError('Result identity/content mismatch')
        return results[0]

    @staticmethod
    def _started(turn):
        payload = {'attempt_id': turn['attempt_id'], 'mode': 'TEST'}
        if turn['schema_version'] == 2:
            payload.update(mode='TEST_OFFLINE', request_ref=turn['prepared']['request_ref'],
                           binding_sha256=turn['binding_sha256'])
        return payload

    @staticmethod
    def _check_usage(usage):
        keys = ('prompt_tokens', 'completion_tokens', 'total_tokens')
        if type(usage) is not dict or set(usage) != {'status', *keys}:
            raise ValueError('Invalid offline usage')
        counts = [usage[key] for key in keys]
        if any(n is not None and (type(n) is not int or n < 0) for n in counts):
            raise ValueError('Invalid offline usage counts')
        known = sum(n is not None for n in counts)
        status = usage['status']
        if ((status == 'complete' and known == 3 and counts[0] + counts[1] == counts[2])
                or (status == 'partial' and known < 3)
                or (status in ('missing', 'invalid') and known == 0)):
            return
        raise ValueError('Invalid offline usage status')

    def _offline_evidence(self, turn, records):
        """Validate the v2 stream against the accepted request and projection."""
        events = [r['event'] for r in records]
        payloads = {r['event']: r['payload'] for r in records}
        if any(type(payload) is not dict for payload in payloads.values()):
            raise ValueError('Invalid offline event payload')
        start = self._started(turn)
        started = 'turn_started' in payloads
        order = ['turn_started'] if started else []
        state = turn['state']
        terminal = None
        if started and payloads['turn_started'] != start:
            raise ValueError('Offline start binding mismatch')
        if turn['cancel_requested']:
            if state not in ('CANCELLED', 'UNKNOWN') or (state == 'CANCELLED' and started):
                raise ValueError('Offline cancellation projection mismatch')
            if 'turn_cancel_requested' in payloads:
                order.append('turn_cancel_requested')
                if payloads['turn_cancel_requested'] != start:
                    raise ValueError('Offline cancellation binding mismatch')
            if started and 'turn_result_discarded' in payloads:
                order.append('turn_result_discarded')
                discarded = payloads['turn_result_discarded']
                self._check_usage(discarded.get('usage'))
                if discarded != {**start, 'usage': discarded['usage']}:
                    raise ValueError('Offline discarded result binding mismatch')
        else:
            for event in ('turn_result', 'turn_failed', 'turn_uncertain'):
                if event not in payloads:
                    continue
                order.append(event)
                payload = payloads[event]
                outcome, execution = payload.get('outcome'), payload.get('execution')
                mapped = OFFLINE_OUTCOMES.get((outcome, execution)) if isinstance(outcome, str) and isinstance(execution, str) else None
                if (not started or mapped is None or mapped[0] != event or terminal is not None
                        or state not in ('ATTEMPTING', mapped[1])):
                    raise ValueError('Offline terminal projection mismatch')
                answer = payload.get('answer')
                if event == 'turn_result':
                    if type(answer) is not str or not answer.strip() or len(answer.encode('utf-8')) > 8192:
                        raise ValueError('Invalid offline answer')
                elif answer is not None:
                    raise ValueError('Answer on unsuccessful offline result')
                self._check_usage(payload.get('usage'))
                if payload != {**start, 'outcome': outcome, 'execution': execution,
                               'usage': payload['usage'], 'answer': answer}:
                    raise ValueError('Offline result binding mismatch')
                terminal = mapped[1], payload
            if terminal is None and (state not in ('ACCEPTING', 'READY', 'ATTEMPTING')
                                     or (started and state != 'ATTEMPTING')):
                raise ValueError('Offline execution projection mismatch')
        if events != order:
            raise ValueError('Unexpected offline event order or multiplicity')
        return terminal

    def _view(self, root, turn, *, records=None):
        state = turn['state']
        if records is None:
            records = self._records(root, turn)  # verify checksums/tails even in a terminal projection
        offline = turn['schema_version'] == 2
        terminal = self._offline_evidence(turn, records) if offline else None
        events = [r['event'] for r in records]
        allowed = {'turn_started','turn_result','turn_failed','turn_cancel_requested','turn_result_discarded'}
        if not offline and (any(event not in allowed for event in events)
                or any(events.count(event)>1 for event in allowed)
                or (state in {'ACCEPTING','READY'} and events)
                or (state=='CANCELLED' and 'turn_started' in events)
                or ('turn_result' in events and ('turn_started' not in events or 'turn_failed' in events))
                or ('turn_failed' in events and 'turn_started' not in events)
                or (state=='FAILED' and 'turn_failed' not in events)
                or (turn['cancel_requested'] and state not in {'CANCELLED','UNKNOWN'})):
            raise ValueError('Turn projection contradicts durable execution facts')
        if state != 'ACCEPTING':
            user = self._raw(root, turn, 'user')
            request = dict(idempotency_key=turn['idempotency_key'],text=user.get('original_text'),**turn['references'])
            if _digest(request) != turn['request_sha256']: raise ValueError('User RAW mismatch')
        if offline and state not in ('ACCEPTING', 'SUCCEEDED'):
            try:
                assistant = self._raw(root, turn, 'assistant')
            except core.StorageReadError as error:
                if error.code != 'missing':
                    raise
            else:
                if not terminal or terminal[0] != 'SUCCEEDED' or assistant.get('original_text') != terminal[1]['answer']:
                    raise ValueError('Offline assistant RAW lacks a matching durable result')
        answer = None
        if state == 'SUCCEEDED':
            answer = terminal[1]['answer'] if offline else ANSWER
            if (turn['cancel_requested'] or (not offline and self._result(root,turn) is None)
                    or self._raw(root,turn,'assistant').get('original_text') != answer):
                raise ValueError('Success not backed by result and RAW')
        if state == 'ATTEMPTING' and not self._is_active(root, turn): state = 'UNKNOWN'
        view = {**{k:turn[k] for k in ('turn_id','run_id','attempt_id','user_message_id','assistant_message_id','idempotency_key')},
                'state':state,'cancel_requested':turn['cancel_requested'],'references':dict(turn['references']),
                'answer':answer,'mode':'TEST'}
        if offline:
            discarded = next((r['payload'] for r in records if r['event'] == 'turn_result_discarded'), None)
            view.update(mode='TEST_OFFLINE', request_ref=turn['prepared']['request_ref'],
                        usage=terminal[1]['usage'] if terminal else discarded['usage'] if discarded else None)
        return view

    def _settle_offline(self, root, turn):
        records = self._records(root, turn)
        view = self._view(root, turn, records=records)
        if turn['state'] == 'ATTEMPTING' and not turn['cancel_requested']:
            terminal = self._offline_evidence(turn, records)
            if terminal:
                state, payload = terminal
                if state == 'SUCCEEDED':
                    self._commit(root, turn, 'assistant', payload['answer'])
                turn['state'] = state
                self._save(root, turn)
                saved = self._load(root, turn['workspace_id'], turn['chat_id'], turn['turn_id'])
                return self._view(root, saved)
        return view

    def _is_active(self, root, turn):
        with self._active_lock: return (str(Path(root).resolve()),turn['turn_id']) in self._active

    def get(self, root, workspace_id, chat_id, turn_id):
        with self._session(root, workspace_id, chat_id):
            return self._view(root, self._load(root,workspace_id,chat_id,turn_id))

    def lookup(self, root, workspace_id, chat_id, key):
        if not isinstance(key,str) or not KEY.fullmatch(key):
            raise UltraChatError(400,'invalid_turn_request','Invalid retry key')
        return self.get(root,workspace_id,chat_id,identities(workspace_id,chat_id,key)['turn_id'])

    def submit(self, root, workspace_id, chat_id, body):
        body = self._body(body)
        ids = identities(workspace_id, chat_id, body['idempotency_key'])
        offline = body['config_ref'] == OFFLINE_REF
        with self._session(root, workspace_id, chat_id):
            summary = runs.load_run_summary(root, ids['run_id'], chat_id)
            if summary is not None and not isinstance(summary, dict):
                raise ValueError('Damaged RUN summary')
            snapshot = None
            if offline and (summary is None or summary.get('turn') is None):
                try:
                    snapshot = self._offline_adapter.freeze(body)
                except ValueError:
                    raise UltraChatError(400, 'invalid_offline_request', 'Offline request could not be prepared') from None
            if summary is None:
                # A crash here has accepted no body/RAW yet; a retry can finish the empty reservation.
                runs.create_run_summary(root, workspace_id, chat_id, ids['task_block_id'], ids['run_id'])
            else:
                if summary.get('workspace_id') != workspace_id: raise ValueError('Foreign RUN')
            summary = runs.load_run_summary(root, ids['run_id'], chat_id)
            if summary.get('turn') is None:
                turn = dict(schema_version=1,workspace_id=workspace_id,chat_id=chat_id,**ids,
                            idempotency_key=body['idempotency_key'],request_sha256=_digest(body),
                            references=dict(REFERENCES),state='ACCEPTING',cancel_requested=False)
                if offline:
                    turn.update(schema_version=2, prepared=snapshot, references={k: body[k] for k in REFERENCES})
                    turn['binding_sha256'] = self._binding(turn)
                self._save(root,turn)
            turn = self._load(root,workspace_id,chat_id,ids['turn_id'])
            if turn['request_sha256'] != _digest(body):
                raise UltraChatError(409,'idempotency_conflict','This key already belongs to different content')
            # This explicit repeat may repair an interrupted append, never execute a started attempt again.
            runs.recover_run_records(root,turn['run_id'])
            if turn['state'] == 'ACCEPTING':
                if offline:
                    self._view(root, turn)
                self._commit(root,turn,'user',body['text'])
                turn['state']='READY'; self._save(root,turn)
            if turn['state'] == 'ATTEMPTING':
                if offline:
                    return self._settle_offline(root, turn)
                if not turn['cancel_requested'] and self._result(root,turn):
                    self._commit(root,turn,'assistant',ANSWER)
                    turn['state']='SUCCEEDED'; self._save(root,turn)
                return self._view(root,turn)
            if turn['state'] != 'READY': return self._view(root,turn)
        return self._execute(root,workspace_id,chat_id,ids['turn_id'])

    @staticmethod
    def _imitate():
        """Fixed local reply. No transport dispatch, plugin/model lookup or external execution."""
        return ANSWER

    def _execute(self, root, workspace_id, chat_id, turn_id):
        active_key = (str(Path(root).resolve()),turn_id)
        with self._session(root,workspace_id,chat_id):
            turn = self._load(root,workspace_id,chat_id,turn_id)
            if turn['state'] != 'READY': return self._view(root,turn)
            self._view(root,turn)  # validate the accepted RAW again immediately before reserving execution
            offline = turn['schema_version'] == 2
            prepared = (self._offline_adapter.restore(turn['prepared'], turn['references'],
                       self._raw(root, turn, 'user')['original_text']) if offline else None)
            turn['state']='ATTEMPTING'; self._save(root,turn)
            start = self._started(turn)
            self._event(root,turn,'turn_started',start)
            with self._active_lock: self._active.add(active_key)
        try:
            if offline:
                return self._execute_offline(root, workspace_id, chat_id, turn_id, start, prepared)
            try:
                answer = self._imitate()  # outside the shared lock; cancellation remains possible
                if answer != ANSWER: raise ValueError('Unexpected TEST answer')
            except Exception:
                with self._session(root,workspace_id,chat_id):
                    turn=self._load(root,workspace_id,chat_id,turn_id)
                    if not turn['cancel_requested']:
                        self._event(root,turn,'turn_failed',{'attempt_id':turn['attempt_id']})
                        turn['state']='FAILED'; self._save(root,turn)
                    return self._view(root,turn)
            with self._session(root,workspace_id,chat_id):
                turn=self._load(root,workspace_id,chat_id,turn_id)
                if turn['state'] != 'ATTEMPTING' or turn['cancel_requested']:
                    self._event(root,turn,'turn_result_discarded',{'attempt_id':turn['attempt_id']})
                    return self._view(root,turn)
                self._event(root,turn,'turn_result',{'attempt_id':turn['attempt_id'],'answer':answer})
                self._commit(root,turn,'assistant',answer)
                turn['state']='SUCCEEDED'; self._save(root,turn)
                return self._view(root,turn)
        finally:
            with self._active_lock: self._active.discard(active_key)

    def _execute_offline(self, root, workspace_id, chat_id, turn_id, start, prepared):
        try:
            result = self._offline_adapter.execute(prepared)
        except Exception:
            # An adapter exception cannot prove that execution never happened.
            result = None
        with self._session(root, workspace_id, chat_id):
            turn = self._load(root, workspace_id, chat_id, turn_id)
            records = self._records(root, turn)
            self._view(root, turn, records=records)
            if (self._started(turn) != start or not records or records[0]['event'] != 'turn_started'
                    or records[0]['payload'] != start):
                raise ValueError('Offline request changed during execution')
            if result is None:
                outcome, execution, answer = 'transport_error', 'may_have_executed', None
                usage = dict(status='missing', prompt_tokens=None, completion_tokens=None, total_tokens=None)
            else:
                if result.request_ref != prepared.request_ref or result.model != prepared.model:
                    raise ValueError('Offline adapter result identity mismatch')
                outcome, execution, answer = result.outcome.value, result.execution.value, result.text
                usage = asdict(result.usage)
            self._check_usage(usage)
            if turn['cancel_requested']:
                event, payload = 'turn_result_discarded', {**start, 'usage': usage}
                self._offline_evidence(turn, [*records, {'event': event, 'payload': payload}])
                self._event(root, turn, event, payload)
                return self._view(root, turn)
            if turn['state'] != 'ATTEMPTING':
                raise ValueError('Offline attempt no longer owns the Turn')
            mapped = OFFLINE_OUTCOMES.get((outcome, execution))
            if mapped is None:
                raise ValueError('Unexpected offline adapter outcome')
            event = mapped[0]
            payload = {**start, 'outcome': outcome, 'execution': execution, 'answer': answer, 'usage': usage}
            self._offline_evidence(turn, [*records, {'event': event, 'payload': payload}])
            self._event(root, turn, event, payload)
            return self._settle_offline(root, turn)

    def cancel(self, root, workspace_id, chat_id, turn_id, body):
        if body != {}: raise UltraChatError(400,'invalid_turn_request','Cancellation body must be empty')
        with self._session(root,workspace_id,chat_id):
            turn=self._load(root,workspace_id,chat_id,turn_id)
            if turn['state'] in {'SUCCEEDED','FAILED','CANCELLED','UNKNOWN'}: return self._view(root,turn)
            runs.recover_run_records(root,turn['run_id'])
            offline = turn['schema_version'] == 2
            if offline:
                view = self._settle_offline(root, turn)
                if turn['state'] in {'SUCCEEDED', 'FAILED', 'UNKNOWN'}:
                    return view
            turn['cancel_requested']=True
            # ACCEPTING has no confirmed user RAW; retain the unaccepted state rather than forge acceptance.
            if turn['state']=='ACCEPTING':
                raise UltraChatError(409,'turn_acceptance_incomplete','Complete acceptance before cancellation')
            turn['state']='UNKNOWN' if turn['state']=='ATTEMPTING' else 'CANCELLED'
            self._save(root,turn)
            self._event(root,turn,'turn_cancel_requested',self._started(turn) if offline else {'attempt_id':turn['attempt_id']})
            return self._view(root,turn)
