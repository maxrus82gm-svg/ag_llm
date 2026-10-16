"""Actual isolated Codex plugin loader and app-server MCP gates. No inference/UI."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

D=Path(__file__).resolve().parent
CLI='C:/Users/REX/AppData/Local/OpenAI/Codex/bin/9614f1d9b40d9c4f/codex.exe'
TOOLS={'ping','list_capabilities','read_synthetic_context'}


class Host:
    def __init__(self,home,work,tag):
        self.home,self.work,self.tag=home,work,tag
        self.serial=0;self.responses={};self.transcript=[]
    async def start(self):
        env=os.environ.copy();env['CODEX_HOME']=str(self.home)
        env['PATH']=os.environ.get('SystemRoot','C:/Windows')+'/System32'
        self.err=(D/(self.tag+'.stderr.log')).open('wb')
        self.p=await asyncio.create_subprocess_exec(CLI,'app-server','--listen','stdio://',
            cwd=self.work,env=env,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=self.err)
        self.reader=asyncio.create_task(self.read())
        await self.call('initialize',{'clientInfo':{'name':'wua_a04_isolated_host','version':'0.2.1'},
                                     'capabilities':{'experimentalApi':True}})
        await self.send({'method':'initialized'})
    async def read(self):
        while line:=await self.p.stdout.readline():
            try:message=json.loads(line)
            except ValueError:continue
            self.transcript.append({'direction':'host_to_test','message':message})
            if 'id' in message and message['id'] in self.responses:
                self.responses[message['id']].set_result(message)
            elif 'id' in message and 'method' in message:
                await self.send({'id':message['id'],'error':{'code':-32000,'message':'No permissions or interactive operations in this isolated read-tool test'}})
    async def send(self,value):
        self.transcript.append({'direction':'test_to_host','message':value})
        self.p.stdin.write((json.dumps(value)+'\n').encode());await self.p.stdin.drain()
    async def call(self,method,params):
        self.serial+=1;identifier=self.serial
        future=asyncio.get_running_loop().create_future();self.responses[identifier]=future
        await self.send({'id':identifier,'method':method,'params':params})
        response=await asyncio.wait_for(future,40)
        if 'error' in response:raise RuntimeError(json.dumps(response['error']))
        return response['result']
    async def close(self):
        self.p.stdin.close()
        try:await asyncio.wait_for(self.p.wait(),10)
        except asyncio.TimeoutError:self.p.terminate();await self.p.wait()
        await self.reader;self.err.close()
        (D/(self.tag+'.rpc.json')).write_text(json.dumps(self.transcript,ensure_ascii=False,indent=2),encoding='utf-8')


def setup(tag,source):
    root=D/'test_environment'/tag;root.mkdir(parents=True,exist_ok=False)
    plugin=root/'plugin';shutil.copytree(source,plugin)
    home=root/'codex_home';home.mkdir()
    catalog=root/'.agents/plugins/marketplace.json';catalog.parent.mkdir(parents=True)
    name='wua-a04-'+tag
    catalog.write_text(json.dumps({'name':name,'plugins':[{'name':'wua-desktop-readonly',
        'source':{'source':'local','path':'./plugin'},'policy':{'installation':'AVAILABLE','authentication':'ON_INSTALL'},'category':'Productivity'}]}),encoding='utf-8')
    env=os.environ.copy();env['CODEX_HOME']=str(home)
    results=[]
    for args in (['plugin','marketplace','add',str(root)],['plugin','add','wua-desktop-readonly@'+name,'--json']):
        r=subprocess.run([CLI,*args],cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',timeout=30)
        results.append({'args':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        if r.returncode:raise RuntimeError(r.stderr)
    return root,home,catalog,results


async def test_case(tag,source,expect_valid):
    root,home,catalog,setup_results=setup(tag,source)
    host=Host(home,root,tag)
    result={'kind':'ACTUAL CODEX HOST PLUGIN LOADER; NOT SDK; NOT ORDINARY CHAT','setup':setup_results}
    await host.start()
    try:
        result['plugin_read']=await host.call('plugin/read',{'marketplacePath':str(catalog),'pluginName':'wua-desktop-readonly'})
        thread=await host.call('thread/start',{'cwd':str(root),'ephemeral':True,'sandbox':'read-only',
                                             'approvalPolicy':'never','experimentalRawEvents':False})
        tid=thread['thread']['id'];result['test_thread_id']=tid
        status=await host.call('mcpServerStatus/list',{'threadId':tid,'detail':'toolsAndAuthOnly'})
        result['mcp_status']=status
        if expect_valid:
            servers=[s for s in status['data'] if set(s.get('tools',{}))==TOOLS]
            assert len(servers)==1, 'Expected exactly one WUA server with three tools: '+json.dumps(status)
            server=servers[0]['name'];result['server_name']=server;result['calls']=[]
            for tool,args in [('ping',{}),('list_capabilities',{}),('read_synthetic_context',{'fixture_id':'synthetic_wua_desktop_001'}),('read_synthetic_context',{'fixture_id':'other_task'})]:
                reply=await host.call('mcpServer/tool/call',{'threadId':tid,'server':server,'tool':tool,'arguments':args})
                result['calls'].append({'tool':tool,'arguments':args,'result':reply})
        result['completed']=True
    finally:
        await host.close()
        (D/(tag+'.result.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


async def main():
    results={}
    for tag,source,valid in [('fixed02',D.parent/'plugin',True)]:
        try:results[tag]=await test_case(tag,source,valid)
        except BaseException as exc:
            results[tag]={'error_type':type(exc).__name__,'error':str(exc)}
            (D/(tag+'.failure.json')).write_text(json.dumps(results[tag],indent=2),encoding='utf-8')
            print(json.dumps({'case':tag,**results[tag]}));return
        print(json.dumps({'case':tag,'completed':True,'mcp_status':results[tag]['mcp_status']}))

if __name__=='__main__':asyncio.run(main())
