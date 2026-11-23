'use strict';
const {spawn,spawnSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const root=process.cwd(),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'wua660-chrome-'));
const python=process.env.WUA_TEST_PYTHON || path.join(root,'.venv','Scripts','python.exe');
const chrome='C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function wait(fn,label,timeout=15000){
 const deadline=Date.now()+timeout;
 while(Date.now()<deadline){try{const v=await fn();if(v)return v}catch(e){}await delay(100)}
 throw Error('timeout '+label)
}
let server,browser,ws,seq=0,pending=new Map(),stderr='',url,info;
async function cdp(method,params={}){
 const id=++seq;
 return new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timeout '+method))},10000);
  pending.set(id,{resolve:r=>{clearTimeout(timer);resolve(r)},reject:e=>{clearTimeout(timer);reject(e)}});
  ws.send(JSON.stringify({id,method,params}));
 })
}
async function evaluate(expression){
 const result=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
 if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);
 return result.result.value
}
const domWait=(expression,label)=>wait(()=>evaluate(expression),label);
async function click(selector){
 assert.equal(await evaluate("(()=>{const e=document.querySelector("+JSON.stringify(selector)+");if(!e||e.disabled)return false;e.click();return true})()"),true,selector);
}
(async()=>{
 try{
  server=spawn(python,['-B','-u','-X','utf8',path.join(__dirname,'chrome_fixture.py'),'--producer-source',process.argv[2]],{cwd:root,windowsHide:true,stdio:['pipe','pipe','pipe']});
  let buf='';
  server.stdout.on('data',b=>{buf+=b.toString('utf8');const m=buf.match(/ORDINARY_TEST_READY ([^\r\n]+)/);if(m){info=JSON.parse(m[1]);url=info.url;}});
  server.stderr.on('data',b=>stderr+=b.toString('utf8'));
  await wait(()=>url,'fixture start');console.log('REAL_TEST_LAUNCHER_FIXTURE_READY');
  browser=spawn(chrome,['--headless=new','--disable-gpu','--disable-extensions','--disable-background-networking','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--user-data-dir='+tmp,'--window-size=1600,900',url],{windowsHide:true,stdio:'ignore'});
  const port=await wait(()=>{const f=path.join(tmp,'DevToolsActivePort');return fs.existsSync(f)&&fs.readFileSync(f,'utf8').split('\n')[0]},'Chrome debug port');
  const target=await wait(async()=>{const a=await (await fetch('http://127.0.0.1:'+port+'/json/list')).json();return a.find(t=>t.type==='page'&&t.url.startsWith(url.split('#')[0]))},'target page');
  ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})});
  ws.addEventListener('message',e=>{const v=JSON.parse(e.data);if(v.id&&pending.has(v.id)){const p=pending.get(v.id);pending.delete(v.id);v.error?p.reject(Error(JSON.stringify(v.error))):p.resolve(v.result)}});
  await cdp('Page.enable');await cdp('Runtime.enable');await cdp('Emulation.setDeviceMetricsOverride',{width:1584,height:805,deviceScaleFactor:1,mobile:false});
  await domWait("typeof chatTurn!=='undefined' && chatTurn.ordinary && chatTurn.colibri && chat.started && chat.chat && !document.querySelector('#chatInput').disabled",'ordinary chat ready',30000);
  assert.equal(await evaluate('chat.chat'),info.chat);
  const local=info.local;
  const original=await evaluate('chat.chat');
  const localChoices=await evaluate("chatTurn.models.filter(x=>x.is_local).map(x=>({id:x.model_id,name:x.display_name,manager:x.manager_name,slot:x.slot_id}))");
  assert.equal(localChoices.length,2);
  assert.notEqual(localChoices[0].id,localChoices[1].id);
  assert.notEqual(localChoices[0].manager,localChoices[1].manager);
  assert.ok(localChoices.some(x=>x.id===info.local));
  console.log('LOCAL_CHOICES_IDENTITY_PASS',JSON.stringify(localChoices));
  async function choose(id){
    await click('#chatModelPick');
    await domWait("document.querySelector('#chatModelMenu [role=option]')",'picker options');
    assert.equal(await evaluate("(()=>{const m=chatTurn.models.find(x=>x.model_id==="+JSON.stringify(id)+");const e=[...document.querySelectorAll('#chatModelMenu [role=option]')].find(x=>x.getAttribute('data-model-id')===m?.model_id);if(!e||e.disabled)return false;if(m.is_local&&(!e.textContent.includes(m.manager_name)||!e.textContent.includes(m.slot_id)))return false;e.click();return true})()"),true);
    await domWait("chatTurn.model==="+JSON.stringify(id)+" && !picker.busy && !document.querySelector('#chatInput').disabled",'model choice');
  }
  async function send(text,count,localTurn=false){
    await evaluate("document.querySelector('#chatInput').value="+JSON.stringify(text)+";true");
    await click('#chatSend');
    if(localTurn){
      await domWait("document.querySelector('#chatColibriReasoning').textContent.includes('Размышление') && chatTurn.busy",'visible reasoning before completion',20000);
      await domWait("document.querySelector('#chatColibriPartial').textContent.includes('Ответ') && !document.querySelector('#chatColibriPartial').hidden && chatTurn.busy",'visible partial answer before completion',20000);
    }
    await domWait("!chatTurn.busy && document.querySelectorAll('#chatHistory .msg').length==="+count,'saved history',25000);
  }
  await choose('gigachat_2_pro');await send('Cloud first',2);
  await choose(local);
  const selectedCaption=await evaluate("document.querySelector('#chatModelPick').textContent");
  const chosen=localChoices.find(x=>x.id===local);
  assert.ok(selectedCaption.includes(chosen.manager)&&selectedCaption.includes(chosen.slot));
  await send('Local second',4,true);
  assert.equal(await evaluate('chat.chat'),original);
  assert.equal(await evaluate("document.querySelector('#chatColibriPartial').hidden"),true);
  assert.equal(await evaluate("document.querySelector('#chatColibriReasoning').textContent.includes('Размышление')"),true);
  await cdp('Page.reload');
  await domWait("typeof chatTurn!=='undefined' && chat.chat==="+JSON.stringify(original)+" && chatTurn.model==="+JSON.stringify(local)+" && document.querySelectorAll('#chatHistory .msg').length===4 && !document.querySelector('#chatInput').disabled",'F5 local choice and history',30000);
  await domWait("document.querySelector('#chatColibriReasoning').textContent.includes('Размышление')",'latest reasoning restored F5');
  // Existing EVM DOM, same persisted switch. Hash navigation is the existing UI route.
  await click('#viewEvm');
  await domWait("document.querySelector('#evmLocalList .ccard[data-connection="+JSON.stringify('local:colibri:'+local)+"]')",'dynamic EVM card',25000);
  const card='#evmLocalList .ccard[data-connection="'+('local:colibri:'+local)+'"]';
  assert.ok((await evaluate("document.querySelector("+JSON.stringify('#evmLocalList .ccard[data-connection="'+('local:colibri:'+local)+'"] .cname')+")?.textContent")).includes(chosen.manager));
  await click(card+' .copen');
  await domWait("document.querySelector("+JSON.stringify(card+" [data-model]")+")",'expanded local card');
  assert.equal(await evaluate("document.querySelector("+JSON.stringify(card+" [data-api]")+")?.getAttribute('data-api')?.startsWith('gray:')"),true);
  const toggle=card+' [data-fk$=":toggle"]';
  await click(toggle);
  await domWait("evm.cards?.cards.find(c=>c.model_id==="+JSON.stringify(local)+")?.enabled===false && !evm.saving",'EVM disabled');
  await click('#viewChat');
  await domWait("chat.chat==="+JSON.stringify(original)+" && chatTurn.model==="+JSON.stringify(local)+" && document.querySelector('#chatSend').disabled",'disable retains choice and blocks send');
  assert.equal(await evaluate("document.querySelectorAll('#chatHistory .msg').length"),4);
  await choose('gigachat_2_max');await send('Cloud third',6);
  assert.equal(await evaluate('chat.chat'),original);
  await cdp('Page.reload');
  await domWait("typeof chatTurn!=='undefined' && chat.chat==="+JSON.stringify(original)+" && chatTurn.model==='gigachat_2_max' && document.querySelectorAll('#chatHistory .msg').length===6",'F5 cloud choice and history',30000);
  const data=await evaluate("({mode:chatTurn.executionMode,history:[...document.querySelectorAll('#chatHistory .msg-text')].map(x=>x.textContent),sameChat:chat.chat==="+JSON.stringify(original)+"})");
  assert.deepEqual(data.history,['Cloud first','H35 synthetic answer','Local second','Ответ','Cloud third','H35 synthetic answer']);
  data.colibriProgress=true;data.evmDisable=true;data.localF5=true;data.cloudF5=true;
  console.log('CHROME_JOINT_PASS',JSON.stringify(data));
  fs.writeFileSync(path.join(__dirname,'chrome-evidence.json'),JSON.stringify(data,null,2)+'\n');
 }catch(e){
   console.error(e.stack);
   try{
     const diag=await evaluate("({view:evm.view,chat:chat.chat,model:chatTurn.model,available:chatTurn.available,busy:chatTurn.busy,execution:chatTurn.executionMode,pickerBusy:picker.busy,pickerOpen:picker.open,disabled:document.querySelector('#chatInput')?.disabled,modelError:document.querySelector('#chatModelError')?.textContent,status:document.querySelector('#chatTurnStatus')?.textContent,menu:[...document.querySelectorAll('#chatModelMenu [role=option]')].map(x=>({name:x.textContent,disabled:x.disabled,selected:x.getAttribute('aria-selected')}))})");
     console.error("CHROME_DIAG "+JSON.stringify(diag));
   }catch(d){console.error("DIAG_UNAVAILABLE "+String(d))}
   if(stderr)console.error(stderr.slice(-1500));process.exitCode=1
 }
 finally{
  if(ws){try{await cdp('Browser.close')}catch(e){}try{ws.close()}catch(e){}}
  if(browser&&browser.exitCode===null){await delay(500);if(browser.exitCode===null)spawnSync('taskkill',['/PID',String(browser.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'})}
  if(server&&server.exitCode===null){server.stdin.write('\n');server.stdin.end();await wait(()=>server.exitCode!==null,'fixture clean stop',10000).catch(()=>{server.kill()});}
  if(server&&server.exitCode!==0){console.error('fixture exit',server.exitCode);process.exitCode=1}
  try{fs.rmSync(tmp,{recursive:true,force:true,maxRetries:2})}catch(e){}
 }
})()
