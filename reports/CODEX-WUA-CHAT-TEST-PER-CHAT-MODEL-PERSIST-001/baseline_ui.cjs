// Reproduce the corrected oracle against the SHA-verified, pre-edit UI backup.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const original=fs.readFileSync;
const saved=JSON.parse(original(path.join(__dirname,'preservation.json'),'utf8'));
const root=path.resolve(__dirname,'../..'),ui=path.join(root,'web_alarm/ui.py');
const data=original(path.join(__dirname,'before_ui.py.txt'));
if(crypto.createHash('sha256').update(data).digest('hex')!==saved.before['web_alarm/ui.py'])throw Error('Baseline changed');
fs.readFileSync=function(file,opts){
  if(typeof file==='string'&&path.resolve(file)===ui){
    const encoding=typeof opts==='string'?opts:opts?.encoding;
    return encoding?data.toString(encoding):Buffer.from(data);
  }
  return original.apply(this,arguments);
};
