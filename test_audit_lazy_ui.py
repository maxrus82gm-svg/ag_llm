import inspect
import json
import queue
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import ultra_ui
from audit_storage import AuditThreadRecorder
from run_store import append_run_record, list_run_records, update_run_summary_index


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
      _render_planner_chat=lambda *a:None,
      planner_diag_request_var=Var(True),planner_diag_context_var=Var(True),
      planner_diag_response_var=Var(True),planner_diag_stages_var=Var(True),
      planner_diag_errors_var=Var(True),executor_diag_context_var=Var(True),
      executor_diag_response_var=Var(True),executor_diag_reset_var=Var(True),
      status_var=Var(),_audit_record_visible=lambda item: True)


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



def bind_audit_methods(app):
    app._audit_filter_flags=lambda: ultra_ui.UltraApp._audit_filter_flags(app)
    app._planner_record_is_error=ultra_ui.UltraApp._planner_record_is_error
    app._audit_record_visible=lambda item: ultra_ui.UltraApp._audit_record_visible(app,item)
    app._export_usage_value=lambda summary,role: ultra_ui.UltraApp._export_usage_value(summary,role)
    app._build_selected_run_export_text=lambda: ultra_ui.UltraApp._build_selected_run_export_text(app)
    return app


def make_export_run(tmp_path: Path):
    task='tb_'+'7'*32
    recorder=AuditThreadRecorder(tmp_path,'ws','chat','run',task_block_id=task,raw_task='TASK')
    events=[
      ('PLANNER','planner_diagnostic_request','REQUEST_VISIBLE'),
      ('PLANNER','planner_diagnostic_context','CONTEXT_HIDDEN'),
      ('PLANNER','planner_diagnostic_response','RESPONSE_VISIBLE'),
      ('SERVER','stage_status_changed','STAGE_VISIBLE'),
      ('EXECUTOR','executor_diagnostic_context','EXEC_CONTEXT_VISIBLE'),
      ('EXECUTOR','executor_diagnostic_response','EXEC_RESPONSE_HIDDEN'),
      ('EXECUTOR','executor_diagnostic_reset','EXEC_RESET_VISIBLE'),
      ('SERVER','tool_finished','TOOL_ALWAYS_VISIBLE'),
      ('DREDD','final_audit_passed','FINAL_ALWAYS_VISIBLE'),
    ]
    for sequence,(source,event,marker) in enumerate(events,1):
        append_run_record(tmp_path,'run',source=source,event=event,
                          payload={'marker':marker},timestamp=sequence)
    update_run_summary_index(tmp_path,'run',{
      'run_status':'SUCCESS','final_audit':'PASS','api_requests':7,'tool_calls':5,
      'usage':{
        'planner':{'calls':1,'prompt_tokens':1,'completion_tokens':1,'total_tokens':10,'complete':True},
        'executor':{'calls':1,'prompt_tokens':1,'completion_tokens':1,'total_tokens':20,'complete':True},
        'dredd':{'calls':1,'prompt_tokens':1,'completion_tokens':1,'total_tokens':30,'complete':True},
        'total':{'calls':3,'prompt_tokens':3,'completion_tokens':3,'total_tokens':60,'complete':True},
      },
    })
    app=bind_audit_methods(fake())
    app.workspace_var=Var(str(tmp_path)); app._selected_task_block_id=task
    return app


def test_v2_visibility_filters_keep_general_facts(tmp_path: Path):
    app=make_export_run(tmp_path)
    records=list_run_records(tmp_path,'run')
    assert all(app._audit_record_visible(item) for item in records)
    app.planner_diag_request_var.set(False)
    app.planner_diag_context_var.set(False)
    app.planner_diag_response_var.set(False)
    app.planner_diag_stages_var.set(False)
    app.executor_diag_context_var.set(False)
    app.executor_diag_response_var.set(False)
    app.executor_diag_reset_var.set(False)
    visible={item['event'] for item in records if app._audit_record_visible(item)}
    assert visible == {'tool_finished','final_audit_passed'}
    ultra_ui.UltraApp._render_audit_thread(app)
    assert {values[2] for values in app.audit_records.rows.values()} == visible
    app.audit_records.rows.clear()
    ultra_ui.UltraApp._refresh_selected_run_index(app)
    assert {values[2] for values in app.audit_records.rows.values()} == visible


def test_planner_error_filter_hides_only_planner_error_records():
    app=bind_audit_methods(fake())
    app.planner_diag_errors_var.set(False)
    assert not app._audit_record_visible({'event':'planner_diagnostic_error'})
    assert not app._audit_record_visible({'event':'mutation_preflight_rejected'})
    assert app._audit_record_visible({'event':'tool_error'})
    assert app._audit_record_visible({'event':'final_audit_failed'})


def test_export_is_filtered_chronological_read_only_and_never_uses_legacy(tmp_path: Path):
    app=make_export_run(tmp_path)
    app.planner_diag_context_var.set(False)
    app.executor_diag_response_var.set(False)
    before={p.relative_to(tmp_path).as_posix():p.read_bytes()
            for p in tmp_path.rglob('*') if p.is_file()}
    with patch.object(ultra_ui,'load_audit_thread') as legacy:
        text=app._build_selected_run_export_text()
    after={p.relative_to(tmp_path).as_posix():p.read_bytes()
           for p in tmp_path.rglob('*') if p.is_file()}
    assert not legacy.called and before==after
    for expected in ('TASK: T-001','RUN: R-001','TASK BLOCK ID: tb_','RUN ID: run',
                     'STATUS: SUCCESS','FINAL AUDIT: PASS','PLANNER: 10','TOTAL: 60',
                     'REQUEST_VISIBLE','TOOL_ALWAYS_VISIBLE','FINAL_ALWAYS_VISIBLE'):
        assert expected in text
    assert 'CONTEXT_HIDDEN' not in text
    assert 'EXEC_RESPONSE_HIDDEN' not in text
    assert text.index('#001') < text.index('#003') < text.index('#009')
    assert 'Planner Context: OFF' in text and 'Executor Response: OFF' in text


def test_copy_export_uses_one_complete_snapshot():
    app=bind_audit_methods(fake())
    app._build_selected_run_export_text=lambda:'FULL EXPORT\n'
    app.clipboard_clear=Mock(); app.clipboard_append=Mock(); app.update_idletasks=Mock()
    with patch.object(ultra_ui,'load_run_summary',return_value={
        'task_display_id':'T-002','run_display_id':'R-003'}):
        ultra_ui.UltraApp._copy_selected_run_export(app)
    app.clipboard_clear.assert_called_once_with()
    app.clipboard_append.assert_called_once_with('FULL EXPORT\n')
    assert app.status_var.get()=='Разбор T-002 / R-003 скопирован в буфер'


def test_save_export_writes_utf8_same_snapshot(tmp_path: Path):
    app=bind_audit_methods(fake())
    app._build_selected_run_export_text=lambda:'ПОЛНЫЙ EXPORT\nline 2\n'
    target=tmp_path/'audit.txt'
    with patch.object(ultra_ui,'load_run_summary',return_value={
          'task_display_id':'T-002','run_display_id':'R-003'}), \
         patch.object(ultra_ui.filedialog,'asksaveasfilename',return_value=str(target)) as dialog:
        ultra_ui.UltraApp._save_selected_run_export(app)
    assert target.read_bytes()=='ПОЛНЫЙ EXPORT\nline 2\n'.encode('utf-8')
    assert dialog.call_args.kwargs['initialfile']=='audit_T-002_R-003.txt'


def test_audit_treeview_uses_dedicated_theme_style():
    build=inspect.getsource(ultra_ui.UltraApp._build_ui)
    theme=inspect.getsource(ultra_ui.UltraApp._apply_theme)
    assert 'style="Audit.Treeview"' in build
    assert '"Audit.Treeview"' in theme
    assert '"Audit.Treeview.Heading"' in theme
    assert 'fieldbackground=field' in theme
