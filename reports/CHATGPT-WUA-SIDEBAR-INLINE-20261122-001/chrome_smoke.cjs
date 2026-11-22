'use strict';
const {spawn,spawnSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const root=process.cwd(),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'wua653-chrome-'));
const python=process.env.WUA_TEST_PYTHON || path.join(root,'.venv','Scripts','python.exe');
const chrome='C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function wait(fn,label,timeout=15000){
 const deadline=Date.now()+timeout;
 while(Date.now()<deadline){try{const v=await fn();if(v)return v}catch(e){}await delay(100)}
 throw Error('timeout '+label)
}
let server,browser,ws,seq=0,pending=new Map(),stderr='',url;
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
  server=spawn(python,['-B','-u','-X','utf8','web_alarm/ordinary_test_fixture.py','--no-browser'],{cwd:root,windowsHide:true,stdio:['pipe','pipe','pipe']});
  let buf='';
  server.stdout.on('data',b=>{buf+=b.toString('utf8');const m=buf.match(/ORDINARY_TEST_READY ([^\r\n]+)/);if(m)url=JSON.parse(m[1]).url;});
  server.stderr.on('data',b=>stderr+=b.toString('utf8'));
  await wait(()=>url,'fixture start');console.log('REAL_TEST_LAUNCHER_FIXTURE_READY');
  browser=spawn(chrome,['--headless=new','--disable-gpu','--disable-extensions','--disable-background-networking','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--user-data-dir='+tmp,'--window-size=1600,900',url],{windowsHide:true,stdio:'ignore'});
  const port=await wait(()=>{const f=path.join(tmp,'DevToolsActivePort');return fs.existsSync(f)&&fs.readFileSync(f,'utf8').split('\n')[0]},'Chrome debug port');
  const target=await wait(async()=>{const a=await (await fetch('http://127.0.0.1:'+port+'/json/list')).json();return a.find(t=>t.type==='page'&&t.url.startsWith(url))},'target page');
  ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})});
  ws.addEventListener('message',e=>{const v=JSON.parse(e.data);if(v.id&&pending.has(v.id)){const p=pending.get(v.id);pending.delete(v.id);v.error?p.reject(Error(JSON.stringify(v.error))):p.resolve(v.result)}});
  await cdp('Page.enable');await cdp('Runtime.enable');await cdp('Emulation.setDeviceMetricsOverride',{width:1584,height:805,deviceScaleFactor:1,mobile:false});
  await domWait("typeof chatTurn!=='undefined' && chatTurn.compact && !document.getElementById('chatPersonalNew').hidden",'personal button visible');
  await click('#chatPersonalNew');
  await domWait("chat.chat && document.querySelectorAll('#chatPersonalList .compact-dialog').length===1 && !document.querySelector('#chatInput').disabled",'personal created, model ready');
  await evaluate("document.querySelector('#chatInput').value='Первое сообщение 123 четыре пять';true");
  await click('#chatSend');
  await domWait("document.querySelector('#chatTitle').textContent==='Первое сообщение 123 четыре' && document.querySelectorAll('#chatHistory .msg').length===2",'first title and actual offline reply');
  const personalRowHeight=await evaluate("document.querySelector('#chatPersonalList .compact-dialog').getBoundingClientRect().height");
  const active=await evaluate('chat.chat');
  await click('#chatPersonalList .compact-edit');
  const personalEditHeight=await evaluate("document.querySelector('#chatPersonalList .compact-dialog').getBoundingClientRect().height");
  assert.equal(personalRowHeight,personalEditHeight);
  assert.equal(await evaluate("document.getElementById('chatNameForm').hidden"),true);
  assert.equal(await evaluate("document.querySelector('#compactInlineName')===document.activeElement"),true);
  await evaluate("(()=>{const e=document.querySelector('#compactInlineName');e.value='Личный тест 42';e.dispatchEvent(new Event('input'));e.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));return true})()");
  await domWait("!document.querySelector('#compactInlineName') && document.querySelector('#chatTitle').textContent==='Личный тест 42'",'inline personal Enter');
  await click('#chatPersonalList .compact-edit');
  await evaluate("(()=>{const e=document.querySelector('#compactInlineName');e.value='discard';e.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));return true})()");
  assert.equal(await evaluate("!document.querySelector('#compactInlineName') && document.querySelector('#chatTitle').textContent==='Личный тест 42'"),true);
  const selection=await evaluate('({chat:chat.chat,epoch:chat.epoch,messages:document.querySelectorAll("#chatHistory .msg").length})');
  assert.equal(active,selection.chat);
  await click('#chatPersonalToggle');
  assert.equal(await evaluate("getComputedStyle(document.querySelector('#chatPersonalList')).display"),'none');
  assert.deepEqual(await evaluate('({chat:chat.chat,epoch:chat.epoch,messages:document.querySelectorAll("#chatHistory .msg").length})'),selection);
  await click('#chatWorkspaceToggle');
  assert.equal(await evaluate("getComputedStyle(document.querySelector('#chatWorkspaceList')).display"),'none');
  await cdp('Page.reload');
  await domWait("typeof chatTurn!=='undefined' && chatTurn.compact && document.querySelector('#chatPersonalList').hidden && document.querySelector('#chatWorkspaceList').hidden && chat.chat",'collapsed persistence F5');
  await click('#chatPersonalToggle');
  await click('#chatRegisterWorkspace');
  await domWait("document.querySelectorAll('#chatWorkspaceList .compact-workspace').length===1 && !chat.chat && !document.querySelector('#chatWorkspaceList').hidden",'empty workspace created and expanded');
  const wsHeight=await evaluate("document.querySelector('.compact-workspace > .chat-workspace-row').getBoundingClientRect().height");
  await click('.compact-workspace > .chat-workspace-row > .compact-edit');
  assert.equal(await evaluate("document.querySelector('.compact-workspace > .chat-workspace-row').getBoundingClientRect().height"),wsHeight);
  assert.equal(await evaluate("document.querySelector('#chatWorkspaceNameForm').hidden"),true);
  await evaluate("(()=>{const e=document.querySelector('#compactInlineName');e.value='Проект тест';e.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));return true})()");
  await domWait("!document.querySelector('#compactInlineName') && document.querySelector('.compact-workspace > .chat-workspace-row').textContent.includes('Проект тест')",'inline workspace Enter');
  console.log('INLINE_AND_COLLAPSE_PASS',JSON.stringify({personalRowHeight,personalEditHeight,wsHeight,selectionPreserved:true,prefsF5:true}));
  const ws1=await evaluate('chat.workspace');
  const group1='.compact-workspace[data-workspace-id="'+ws1+'"]';
  const before=await evaluate("(()=>{const g=document.querySelector('.compact-workspace');return {width:g.getBoundingClientRect().width,height:g.getBoundingClientRect().height}})()");
  await click('.compact-workspace .compact-folder-icon');
  await domWait("document.querySelector('.compact-folder small').textContent.startsWith('TEST ·')",'folder association');
  await click('.compact-workspace .compact-plus');
  await domWait("document.querySelectorAll('.compact-workspace .compact-dialog').length===1 && chat.chat && !chatEdit.busy",'workspace chat one');
  const nestedHeight=await evaluate("document.querySelector('.compact-workspace .compact-dialog').getBoundingClientRect().height");
  await click('.compact-workspace .compact-dialog .compact-edit');
  assert.equal(await evaluate("document.querySelector('.compact-workspace .compact-dialog').getBoundingClientRect().height"),nestedHeight);
  await evaluate("(()=>{const e=document.querySelector('#compactInlineName');e.value='Вложенный тест';e.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));return true})()");
  await domWait("!document.querySelector('#compactInlineName') && document.querySelector('#chatTitle').textContent==='Вложенный тест'",'inline nested Enter');
  const one=await evaluate("(()=>{const g=document.querySelector('.compact-workspace');return {width:g.getBoundingClientRect().width,height:g.getBoundingClientRect().height}})()");
  await click('.compact-workspace .compact-plus');
  await domWait("document.querySelectorAll('.compact-workspace .compact-dialog').length===2 && !chatEdit.busy",'workspace chat two');
  const two=await evaluate("(()=>{const g=document.querySelector('.compact-workspace'),r=g.querySelector('.compact-dialog');return {width:g.getBoundingClientRect().width,height:g.getBoundingClientRect().height,rowHeight:r.getBoundingClientRect().height,overflow:g.scrollWidth>g.clientWidth}})()");
  assert.equal(before.width,one.width);assert.equal(one.width,two.width);assert.ok(one.height>before.height);assert.ok(two.height>one.height);assert.equal(two.overflow,false);
  assert.ok(Math.abs((two.height-one.height)-two.rowHeight)<6);
  await click('#chatRegisterWorkspace');
  await domWait("document.querySelectorAll('#chatWorkspaceList .compact-workspace').length===2 && !chat.creatingWorkspace",'workspace two');
  assert.equal(await evaluate("document.querySelector("+JSON.stringify(group1)+").querySelectorAll('.compact-dialog').length"),2);
  assert.equal(await evaluate("document.querySelectorAll('#chatPersonalList .compact-dialog').length"),1);
  assert.equal(await evaluate("document.querySelector('#chatNameForm').hidden && document.querySelector('#chatTestWorkspaceForm').hidden"),true);
  const shot=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  fs.writeFileSync(path.join(root,'reports','CHATGPT-WUA-SIDEBAR-INLINE-20261122-001','offline-preview.png'),Buffer.from(shot.data,'base64'));
  await evaluate("window.confirm=()=>true;true");
  await click(group1+' .compact-dialog .compact-trash');
  await domWait("document.querySelector("+JSON.stringify(group1)+").querySelectorAll('.compact-dialog').length===1 && !chatEdit.busy",'archive chat');
  await click(group1+' > .chat-workspace-row > .compact-trash');
  await domWait("document.querySelectorAll('#chatWorkspaceList .compact-workspace').length===1 && !chatEdit.busy",'archive workspace');
  await cdp('Page.reload');
  await domWait("typeof chatTurn!=='undefined' && chatTurn.compact && document.querySelectorAll('#chatWorkspaceList .compact-workspace').length===1 && document.querySelectorAll('#chatPersonalList .compact-dialog').length===1",'reload persistence');
  console.log('CHROME_PHYSICAL_PASS',JSON.stringify({before,one,two,personal:true,firstTitle:true,personalReply:true,archiveF5:true,allWorkspaceRowsVisible:true,inlineRename:true,unchangedRowHeight:true,collapseF5:true}));
  fs.writeFileSync(path.join(root,'reports','CHATGPT-WUA-SIDEBAR-INLINE-20261122-001','chrome-evidence.json'),JSON.stringify({before,one,two,personal:true,firstTitle:true,personalReply:true,archiveF5:true,allWorkspaceRowsVisible:true,inlineRename:true,unchangedRowHeight:true,collapseF5:true},null,2));
 }catch(e){console.error(e.stack);if(stderr)console.error(stderr.slice(-1500));process.exitCode=1}
 finally{
  if(ws){try{await cdp('Browser.close')}catch(e){}try{ws.close()}catch(e){}}
  if(browser&&browser.exitCode===null){await delay(500);if(browser.exitCode===null)spawnSync('taskkill',['/PID',String(browser.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'})}
  if(server&&server.exitCode===null){server.stdin.write('\n');server.stdin.end();await wait(()=>server.exitCode!==null,'fixture clean stop',10000).catch(()=>{server.kill()});}
  if(server&&server.exitCode!==0){console.error('fixture exit',server.exitCode);process.exitCode=1}
  try{fs.rmSync(tmp,{recursive:true,force:true,maxRetries:2})}catch(e){}
 }
})()
