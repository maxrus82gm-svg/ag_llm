"""Stage 3 TEST Turns. Identity/projection in the existing RUN summary, events in Run Store, RAW in Ultra.

No provider imports, arbitrary adapters, hidden retries, or execution from GET. A lost owner is UNKNOWN;
only an already durable result can be published on an explicit repeat of the same request.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
from pathlib import Path
import re
import threading
import time

import context_storage as core
import run_store as runs
from .ultra_chat import UltraChatError

REFERENCES = {'model_ref': 'local-test:v1', 'context_ref': 'empty:v1', 'config_ref': 'test-only:v1'}
ANSWER = 'TEST: сообщение принято.'
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
    def __init__(self, *, test_roots=()):
        self.test_roots = frozenset(Path(p).resolve() for p in test_roots)
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

    @staticmethod
    def _body(body):
        try:
            text_size = len(body['text'].encode('utf-8')) if isinstance(body,dict) and isinstance(body.get('text'),str) else 0
        except UnicodeError:
            raise UltraChatError(400,'invalid_turn_request','Text must be valid Unicode') from None
        if (not isinstance(body, dict) or set(body) != {'idempotency_key', 'text', *REFERENCES}
                or not isinstance(body['idempotency_key'], str) or not KEY.fullmatch(body['idempotency_key'])
                or not isinstance(body['text'], str) or not body['text'].strip()
                or text_size > 2048):
            raise UltraChatError(400, 'invalid_turn_request', 'Expected a small message and a stable retry key')
        if any(body[k] != v for k, v in REFERENCES.items()):
            raise UltraChatError(409, 'invalid_turn_reference', 'Only the explicit TEST references are allowed')
        return copy.deepcopy(body)

    @staticmethod
    def _load(root, workspace_id, chat_id, turn_id):
        if not isinstance(turn_id, str) or not TURN.fullmatch(turn_id):
            raise UltraChatError(400, 'invalid_turn_id', 'Invalid Turn ID')
        summary = runs.load_run_summary(root, turn_id, chat_id)
        if summary is None:
            raise UltraChatError(404, 'turn_not_found', 'Turn is not in this Chat')
        turn = summary.get('turn')
        if turn is None:
            raise UltraChatError(409, 'turn_acceptance_incomplete', 'Repeat the original request to finish acceptance')
        if (not isinstance(turn, dict) or turn.get('schema_version') != 1
                or summary.get('workspace_id') != workspace_id or turn.get('workspace_id') != workspace_id
                or turn.get('chat_id') != chat_id or turn.get('state') not in STATES
                or not isinstance(turn.get('idempotency_key'), str) or not KEY.fullmatch(turn['idempotency_key'])
                or not isinstance(turn.get('request_sha256'), str) or not re.fullmatch('[0-9a-f]{64}',turn['request_sha256'])
                or turn.get('references') != REFERENCES
                or any(turn.get(k) != v for k, v in identities(workspace_id,chat_id,turn['idempotency_key']).items())
                or turn.get('turn_id') != turn_id or type(turn.get('cancel_requested')) is not bool):
            raise ValueError('Damaged Turn binding')
        return turn

    @staticmethod
    def _save(root, turn):
        state = turn['state']
        runs.update_run_summary_index(root, turn['run_id'], {'turn': turn, 'run_status':
            'COMPLETED' if state == 'SUCCEEDED' else state if state in {'FAILED','CANCELLED','UNKNOWN'} else 'RUNNING'})

    @staticmethod
    def _event(root, turn, event, payload):
        return runs.append_run_record(root, turn['run_id'], source='SERVER', event=event,
                                      payload=payload, timestamp=time.time())

    @staticmethod
    def _raw(root, turn, role):
        message_id = turn[role+'_message_id']
        value = core.read_ultra_json_bounded(root, ('chats', turn['chat_id'], 'messages', message_id+'.json'), max_bytes=32768)
        producer = {'kind': 'test_imitation', 'run_id': turn['run_id'], 'turn_id': turn['turn_id'],
                    'model_display_name': 'TEST · локальный имитатор'}
        if (value.get('workspace_id') != turn['workspace_id'] or value.get('chat_id') != turn['chat_id']
                or value.get('message_id') != message_id or value.get('role') != ('user' if role == 'user' else 'assistant')
                or value.get('producer') != producer or value.get('task_block_id') != turn['task_block_id']):
            raise ValueError('RAW identity mismatch')
        return value

    @staticmethod
    def _commit(root, turn, role, text):
        core.commit_raw_message(root, turn['chat_id'], turn[role+'_message_id'], role, text,
            expected_workspace_id=turn['workspace_id'], task_block_id=turn['task_block_id'],
            producer={'kind':'test_imitation','run_id':turn['run_id'],'turn_id':turn['turn_id'],
                      'model_display_name':'TEST · локальный имитатор'})

    def _records(self, root, turn):
        return runs.load_stream_records(root, turn['run_id'], 'SERVER')

    def _result(self, root, turn):
        results = [r for r in self._records(root, turn) if r['event'] == 'turn_result']
        if not results: return None
        if len(results) != 1 or results[0]['payload'] != {'attempt_id':turn['attempt_id'],'answer':ANSWER}:
            raise ValueError('Result identity/content mismatch')
        return results[0]

    def _view(self, root, turn):
        state = turn['state']
        records = self._records(root, turn)  # verify checksums/tails even in a terminal projection
        events = [r['event'] for r in records]
        allowed = {'turn_started','turn_result','turn_failed','turn_cancel_requested','turn_result_discarded'}
        if (any(event not in allowed for event in events)
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
            request = dict(idempotency_key=turn['idempotency_key'],text=user['original_text'],**turn['references'])
            if _digest(request) != turn['request_sha256']: raise ValueError('User RAW mismatch')
        if state == 'SUCCEEDED':
            if turn['cancel_requested'] or self._result(root,turn) is None or self._raw(root,turn,'assistant')['original_text'] != ANSWER:
                raise ValueError('Success not backed by result and RAW')
        if state == 'ATTEMPTING' and not self._is_active(root, turn): state = 'UNKNOWN'
        return {**{k:turn[k] for k in ('turn_id','run_id','attempt_id','user_message_id','assistant_message_id','idempotency_key')},
                'state':state,'cancel_requested':turn['cancel_requested'],'references':dict(turn['references']),
                'answer':ANSWER if state == 'SUCCEEDED' else None,'mode':'TEST'}

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
        with self._session(root, workspace_id, chat_id):
            summary = runs.load_run_summary(root, ids['run_id'], chat_id)
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
                self._save(root,turn)
            turn = self._load(root,workspace_id,chat_id,ids['turn_id'])
            if turn['request_sha256'] != _digest(body):
                raise UltraChatError(409,'idempotency_conflict','This key already belongs to different content')
            # This explicit repeat may repair an interrupted append, never execute a started attempt again.
            runs.recover_run_records(root,turn['run_id'])
            if turn['state'] == 'ACCEPTING':
                self._commit(root,turn,'user',body['text'])
                turn['state']='READY'; self._save(root,turn)
            if turn['state'] == 'ATTEMPTING':
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
            turn['state']='ATTEMPTING'; self._save(root,turn)
            self._event(root,turn,'turn_started',{'attempt_id':turn['attempt_id'],'mode':'TEST'})
            with self._active_lock: self._active.add(active_key)
        try:
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

    def cancel(self, root, workspace_id, chat_id, turn_id, body):
        if body != {}: raise UltraChatError(400,'invalid_turn_request','Cancellation body must be empty')
        with self._session(root,workspace_id,chat_id):
            turn=self._load(root,workspace_id,chat_id,turn_id)
            if turn['state'] in {'SUCCEEDED','FAILED','CANCELLED','UNKNOWN'}: return self._view(root,turn)
            runs.recover_run_records(root,turn['run_id'])
            turn['cancel_requested']=True
            # ACCEPTING has no confirmed user RAW; retain the unaccepted state rather than forge acceptance.
            if turn['state']=='ACCEPTING':
                raise UltraChatError(409,'turn_acceptance_incomplete','Complete acceptance before cancellation')
            turn['state']='UNKNOWN' if turn['state']=='ATTEMPTING' else 'CANCELLED'
            self._save(root,turn)
            self._event(root,turn,'turn_cancel_requested',{'attempt_id':turn['attempt_id']})
            return self._view(root,turn)
