#!/usr/bin/env python3
"""Extend existing host refresh and its policy with NVIDIA read access only."""
import shlex
import subprocess

REMOTE=r'''
import json,pathlib,py_compile
p=pathlib.Path('/opt/ai-aggregator/bootstrap/vault-runtime.py')
source=p.read_text()
marker='# NVIDIA models: generated from non-secret host declaration'
if marker not in source:
 old="'litellm/providers/anthropic', 'litellm/providers/xai'):"
 if old not in source:raise SystemExit('Unexpected Vault refresh source; unchanged')
 source=source.replace(old,"'litellm/providers/anthropic', 'litellm/providers/xai', 'litellm/providers/nvidia'):",1)
 old="    # JSON is valid YAML and avoids interpolation of secret characters."
 if old not in source:raise SystemExit('Unexpected renderer source; unchanged')
 addition="""    # NVIDIA models: generated from non-secret host declaration
    nv = data['litellm/providers/nvidia']
    current_env = dict(line.split('=', 1) for line in (RUN / 'litellm.env').read_text().splitlines() if '=' in line)
    values = {key: json.loads(value) for key, value in current_env.items()}
    values['NVIDIA_API_KEY'] = nv['api_key']
    write(RUN / 'litellm.env', env(values))
    for model in CFG.get('nvidia_models', []):
        models.append({'model_name': model, 'litellm_params': {'model': 'nvidia_nim/' + model,
            'api_key': 'os.environ/NVIDIA_API_KEY', 'api_base': nv['endpoint'].rstrip('/')}})
"""
 source=source.replace(old,addition+old,1)
 compile(source,str(p),'exec')
 backup=p.with_suffix('.py.pre-nvidia')
 if not backup.exists():backup.write_text(p.read_text())
 p.write_text(source)
cfgpath=pathlib.Path('/etc/ai-aggregator/home-lab.json');cfg=json.loads(cfgpath.read_text())
cfg['nvidia_models']=['openai/gpt-oss-20b','nvidia/nemotron-3.5-lightning-30b-a3b','deepseek-ai/deepseek-v4.1-flash','z-ai/glm-5.3','z-ai/glm-5.3-flash']
cfgpath.write_text(json.dumps(cfg,indent=2)+'\n')
print('Persistent non-secret model declaration and Vault renderer updated')
'''

def main():
    name='ai-aggregator-homelab-uat'
    old=subprocess.run(['vault','policy','read','-address=https://vault.svc.plus',name],capture_output=True,text=True,check=True).stdout
    path='kv/data/uat/ai-aggregator/litellm/providers/nvidia'
    if 'path "'+path+'"' not in old:
        policy=old+'\npath "'+path+'" { capabilities = ["read"] }\n'
        subprocess.run(['vault','policy','write','-address=https://vault.svc.plus',name,'-'],input=policy,text=True,capture_output=True,check=True)
    p=subprocess.run(['ssh','-o','BatchMode=yes','root@10.79.0.7','python3 -c '+shlex.quote(REMOTE)],capture_output=True,text=True)
    print(p.stdout)
    if p.returncode:raise SystemExit('Persistence update failed')

if __name__=='__main__':main()
