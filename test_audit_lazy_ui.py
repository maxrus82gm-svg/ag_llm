import inspect
import queue
from types import SimpleNamespace
from unittest.mock import Mock, patch

import ultra_ui


class Var:
    def __init__(self,v=None): self.v=v
    def get(self): return self.v
    def set(self,v): self.v=v


class Text:
    def __init__(self): self.value=''
    def configure(self,**kw): pass
    def delete(self,*a): self.value=''
    def insert(self,_at,text,*a): self.value+=text
    def see(self,*a): pass


class Tree:
    def __init__(self): self.rows={}; self.selected=()
    def get_children(self): return tuple(self.rows)
    def delete(self,item): self.rows.pop(item,None)
    def insert(self,*a,**kw): self.rows[kw['iid']]=kw['values']
    def selection(self): return self.selected


def fake():
    return SimpleNamespace(audit_text=Text(),audit_records=Tree(),audit_summary_var=Var(),
      _selected_audit_run_id='run',_selected_task_block_id='task',current_chat_id='chat',
      current_workspace_id='ws',workspace_var=Var('/workspace'),
      _audit_summary_text=lambda summary: ultra_ui.UltraApp._audit_summary_text(None, summary),
      _render_planner_chat=lambda *a:None)


def test_chat_startup_has_no_full_audit_listing():
    source=inspect.getsource(ultra_ui.UltraApp._render_current_chat_body)
    assert 'list_chat_audit_threads' not in source
    assert 'load_audit_thread' not in source


def test_selected_run_loads_summary_index_then_one_record():
    app=fake(); summary={'task_display_id':'T-001','run_display_id':'R-001','usage':{}}
    idx=[{'record_id':'rec_1','sequence':1,'source':'SERVER','event':'run_started'}]
    with patch.object(ultra_ui,'load_run_summary',return_value=summary), \
         patch.object(ultra_ui,'list_run_records',return_value=idx), \
         patch.object(ultra_ui,'load_run_record',return_value={'record_id':'rec_1'}) as one, \
         patch.object(ultra_ui,'load_audit_thread') as full:
        ultra_ui.UltraApp._render_audit_thread(app)
        assert not one.called and not full.called
        app.audit_records.selected=('rec_1',)
        ultra_ui.UltraApp._on_audit_record_selected(app)
        one.assert_called_once()


def test_planner_chat_reads_only_planner_stream():
    app=fake(); app.planner_chat_text=Text(); app.planner_chat_status_var=Var()
    records=[{'event':'planner_session_message','payload':{'speaker':'PLANNER','text':'plan','session_id':'s'}}]
    with patch.object(ultra_ui,'load_stream_records',return_value=records) as stream, \
         patch.object(ultra_ui,'load_audit_thread') as full:
        ultra_ui.UltraApp._render_planner_chat(app)
        stream.assert_called_once_with('/workspace','run','PLANNER')
        assert not full.called and 'plan' in app.planner_chat_text.value


def test_trace_limit_constant():
    assert ultra_ui.MAX_TRACE_WIDGET_LINES==500
