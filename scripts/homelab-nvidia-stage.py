#!/usr/bin/env python3
"""Stage Vault NVIDIA credentials on Home-Lab tmpfs and register its channel."""
import json
import shlex
import subprocess

REMOTE = r'''
import json,os,pathlib,pwd,subprocess,sys,time,urllib.request
c=json.load(sys.stdin)
if c['endpoint'].rstrip('/')!='https://integrate.api.nvidia.com/v1':raise SystemExit('Unexpected endpoint')
models=['openai/gpt-oss-20b','nvidia/nemotron-3.5-lightning-30b-a3b','deepseek-ai/deepseek-v4.1-flash','z-ai/glm-5.3','z-ai/glm-5.3-flash']
root=pathlib.Path('/run/ai-aggregator')
fs=subprocess.check_output(['findmnt','-n','-o','FSTYPE','-T',str(root)],text=True).strip()
if fs!='tmpfs':raise SystemExit('Runtime directory is not tmpfs')
def atomic(path,text,owner):
 p=path.with_suffix(path.suffix+'.new');p.write_text(text);os.chmod(p,0o600);u=pwd.getpwnam(owner);os.chown(p,u.pw_uid,u.pw_gid);os.replace(p,path)
envpath=root/'litellm.env'
lines=[l for l in envpath.read_text().splitlines() if not l.startswith('NVIDIA_API_KEY=')]
lines.append('NVIDIA_API_KEY='+json.dumps(c['api_key']))
confpath=root/'litellm.yaml';conf=json.loads(confpath.read_text())
previous={m['model_name']:m for m in conf.get('model_list',[])}
for model in models:
 previous[model]={'model_name':model,'litellm_params':{'model':'nvidia_nim/'+model,'api_base':c['endpoint'].rstrip('/'),'api_key':'os.environ/NVIDIA_API_KEY'}}
conf['model_list']=list(previous.values())
atomic(envpath,'\n'.join(lines)+'\n','root');atomic(confpath,json.dumps(conf),'aiagg-litellm')
subprocess.run(['systemctl','restart','ai-aggregator-litellm.service'],check=True)
env={}
for line in envpath.read_text().splitlines():
 if '=' in line:
  k,v=line.split('=',1)
  try:env[k]=json.loads(v)
  except Exception:env[k]=v
for attempt in range(30):
 try:
  req=urllib.request.Request('http://127.0.0.1:4000/v1/models',headers={'Authorization':'Bearer '+env['LITELLM_MASTER_KEY']})
  listed=json.load(urllib.request.urlopen(req,timeout=5));break
 except Exception:time.sleep(2)
else:raise SystemExit('LiteLLM readiness failed; channel not registered')
print('LiteLLM catalog:',[m['id'] for m in listed.get('data',[])],flush=True)
b=json.loads((root/'bootstrap.json').read_text())['gateway/new-api']
req=urllib.request.Request('http://127.0.0.1:3000/api/user/login',data=json.dumps({'username':b['bootstrap_admin_username'],'password':b['bootstrap_admin_password']}).encode(),headers={'Content-Type':'application/json'})
s=json.load(urllib.request.urlopen(req,timeout=15))['data'];headers={'Authorization':'Bearer '+s['access_token'],'New-Api-User':str(s['user']['id']),'Content-Type':'application/json'}
items=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:3000/api/channel/?p=0&size=100',headers=headers),timeout=15))['data']['items']
channel={'name':'litellm-nvidia-open-models','type':1,'status':1,'base_url':'http://127.0.0.1:4000','key':env['LITELLM_MASTER_KEY'],'models':','.join(models),'group':'default','priority':0,'weight':10}
existing=next((x for x in items if x['name']==channel['name']),None)
if existing:channel['id']=existing['id'];payload=channel;method='PUT'
else:payload={'mode':'single','channel':channel};method='POST'
req=urllib.request.Request('http://127.0.0.1:3000/api/channel/',data=json.dumps(payload).encode(),headers=headers,method=method)
result=json.load(urllib.request.urlopen(req,timeout=20));print('Channel registration success:',result.get('success'),flush=True)
if not result.get('success'):raise SystemExit('Channel registration rejected')
'''

def main():
    p=subprocess.run(['vault','kv','get','-address=https://vault.svc.plus','-format=json','kv/uat/ai-aggregator/litellm/providers/nvidia'],capture_output=True,text=True)
    if p.returncode:raise SystemExit('Vault NVIDIA read failed')
    credentials=json.loads(p.stdout)['data']['data']
    p=subprocess.run(['ssh','-o','BatchMode=yes','root@10.79.0.7','python3 -c '+shlex.quote(REMOTE)],input=json.dumps(credentials),text=True,capture_output=True)
    print(p.stdout)
    if p.returncode:print('Remote stage failed; inspect sanitized service status')
    return p.returncode

if __name__=='__main__':raise SystemExit(main())
