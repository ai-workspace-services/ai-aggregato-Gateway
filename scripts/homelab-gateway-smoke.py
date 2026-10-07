#!/usr/bin/env python3
"""Probe the deployed Home-Lab gateway catalog; credentials stay on host."""
import json
import pathlib
import shlex
import subprocess
import sys

REMOTE = r'''
import concurrent.futures,json,sys,time,urllib.request,urllib.error
import pathlib
admin=json.loads(pathlib.Path('/run/ai-aggregator/bootstrap.json').read_text())['gateway/new-api']
login=urllib.request.Request('http://127.0.0.1:3000/api/user/login',data=json.dumps({'username':admin['bootstrap_admin_username'],'password':admin['bootstrap_admin_password']}).encode(),headers={'Content-Type':'application/json'})
session=json.load(urllib.request.urlopen(login,timeout=15))['data']
ah={'Authorization':'Bearer '+session['access_token'],'New-Api-User':str(session['user']['id'])}
tokens=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:3000/api/token/?p=0&size=100',headers=ah),timeout=15))['data']['items']
token=next(t for t in tokens if t['name']=='Home-Lab' and t['status']==1)
req=urllib.request.Request('http://127.0.0.1:3000/api/token/'+str(token['id'])+'/key',data=b'{}',headers={**ah,'Content-Type':'application/json'})
key=json.load(urllib.request.urlopen(req,timeout=15))['data']['key']
base='https://ai-internal.onwalk.net/v1'
headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'}
with urllib.request.urlopen(urllib.request.Request(base+'/models',headers=headers),timeout=30) as r:
 ids=sorted({m['id'] for m in json.load(r)['data']})
print(json.dumps({'catalog_count':len(ids)}),flush=True)
def probe(model):
 start=time.monotonic()
 result={'model':model}
 try:
  payload={'model':model,'messages':[{'role':'user','content':'Say hello in one short sentence.'}],'max_tokens':512,'stream':False}
  req=urllib.request.Request(base+'/chat/completions',data=json.dumps(payload).encode(),headers=headers)
  with urllib.request.urlopen(req,timeout=120) as r:
   data=json.load(r);choice=data.get('choices',[{}])[0];message=choice.get('message',{})
   content=message.get('content')
   status='pass' if isinstance(content,str) and content.strip() else 'empty_content'
   if isinstance(content,str) and any(s in content.lower() for s in ['no longer available','please switch to','model is deprecated']):status='unavailable_notice'
   result.update(http=r.status,status=status,reply=content[:200] if isinstance(content,str) else None,finish_reason=choice.get('finish_reason'),reasoning_present=bool(message.get('reasoning_content')))
 except urllib.error.HTTPError as e:
  result.update(http=e.code,status='http_error')
  try:
   err=json.loads(e.read()).get('error',{})
   if isinstance(err,dict):result['error_code']=err.get('code');result['error_type']=err.get('type')
  except Exception:pass
 except Exception as e:result.update(status='request_error',error_type=type(e).__name__)
 result['seconds']=round(time.monotonic()-start,2)
 return result
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 futures=[pool.submit(probe,m) for m in ids]
 for f in concurrent.futures.as_completed(futures):print(json.dumps(f.result(),ensure_ascii=False),flush=True)
'''

def main():
    child=subprocess.Popen(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','root@10.79.0.7','python3 -c '+shlex.quote(REMOTE)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    child.stdin.close()
    results=[]
    catalog=None
    for line in child.stdout:
        item=json.loads(line)
        if 'catalog_count' in item:catalog=item['catalog_count']
        else:results.append(item)
        print(line.rstrip(),flush=True)
    exit_code=child.wait()
    target=pathlib.Path(sys.argv[1])
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'catalog_count':catalog,'ssh_exit':exit_code,'results':sorted(results,key=lambda r:r['model'])},ensure_ascii=False,indent=2)+'\n')
    print('Report: '+str(target),flush=True)
    return exit_code

if __name__=='__main__':raise SystemExit(main())
