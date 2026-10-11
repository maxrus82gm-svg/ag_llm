"""Reproducible WA4-O browser fixture, restricted to an EMPTY temp directory.

Not a production launcher. All state and simulated project writes are disposable.
Stop with Ctrl+C; no network except the loopback HTTP listener is used.
"""
import argparse
import json
import tempfile
from pathlib import Path

from web_alarm.server import WebAlarmApi, create_server


def build_fixture(root):
    root = Path(root).resolve()
    temp = Path(tempfile.gettempdir()).resolve()
    if not root.is_relative_to(temp) or root == temp or (root.exists() and any(root.iterdir())):
        raise ValueError('fixture requires an empty child of the system temp directory')
    root.mkdir(parents=True, exist_ok=True)
    api = WebAlarmApi(root/'storage')
    for wid, name in [('ws_delivery','Доставка и интеграция'),('ws_lab','Лаборатория')]:
        project = root/wid
        project.mkdir()
        (project/'config.txt').write_bytes(b'before\n')
        api.registry.register(name,project,workspace_id=wid)
    def task(tid, title, wid, stages):
        api.tasks.create_task(wid,title,'Disposable visual acceptance. <script>alert(1)</script>',
                              'Проверить устойчивое продолжение работы и сохранить доказательства каждого этапа.',task_id=tid)
        for i, name in enumerate(stages,1):
            api.tasks.create_microtask(tid,name,'Выполнить этап в утверждённом scope и сохранить проверяемый результат.',microtask_id='m'+str(i))
    def advance(tid, mid, end):
        api.machine.prepare_microtask(tid,mid,[('config.txt','edit')])
        for status in ['READY','ACTIVE','DONE','VERIFIED']:
            api.machine.transition(tid,mid,status,verification_evidence='Disposable fixture: exact bytes inspected' if status=='VERIFIED' else None)
            if status == end:
                break
    task('task_delivery','Обновление конфигурации сервиса','ws_delivery',
         ['Проверка исходных данных','Подготовка контрактов','Применение конфигурации','Регрессионная проверка','Независимая приёмка','Закрытие TASK'])
    advance('task_delivery','m1','VERIFIED')
    advance('task_delivery','m2','VERIFIED')
    advance('task_delivery','m3','ACTIVE')
    api.operations.begin('task_delivery','m3','write','config.txt',operation_id='op_config_003',payload=b'after\n')
    api.operations.transition('task_delivery','op_config_003','STARTED')
    (root/'ws_delivery'/'config.txt').write_bytes(b'partially changed\n')
    api.operations.transition('task_delivery','op_config_003','UNKNOWN_AFTER_DISCONNECT')
    api.machine.transition('task_delivery','m3','UNKNOWN_AFTER_DISCONNECT')
    task('task_review','Проверка подключения','ws_delivery',['Подключение','Проверка'])
    advance('task_review','m1','DONE')
    task('task_lab','Исследование протокола','ws_lab',['Подготовка','Эксперимент'])
    task('task_closed','Завершённая проверка контракта','ws_delivery',['Приёмка'])
    advance('task_closed','m1','VERIFIED')
    api.dispatch('POST','/tasks/task_closed/complete',{})
    return api


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    server = create_server(build_fixture(args.root),port=args.port)
    print(json.dumps({'url':'http://127.0.0.1:'+str(server.server_port), 'root':str(Path(args.root).resolve())}),flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
