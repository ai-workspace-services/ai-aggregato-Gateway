#!/usr/bin/env python3
"""Register explicitly verified Ollama Cloud models; secrets stay in Vault/tmpfs."""
import argparse
import json
import shlex
import subprocess

REMOTE = r'''
import json, os, pathlib, pwd, subprocess, sys, time, urllib.request
c = json.load(sys.stdin)
models = c.pop('models')
root = pathlib.Path('/run/ai-aggregator')
if subprocess.check_output(['findmnt', '-n', '-o', 'FSTYPE', '-T', str(root)], text=True).strip() != 'tmpfs':
    raise SystemExit('Expected tmpfs runtime')
def atomic(path, value, owner='root'):
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    temp = path.with_name(path.name + '.ollama-new')
    temp.write_text(value)
    os.chmod(temp, mode)
    u = pwd.getpwnam(owner)
    os.chown(temp, u.pw_uid, u.pw_gid)
    os.replace(temp, path)
def call(url, headers, value=None, method=None):
    req = urllib.request.Request(url, headers=headers, data=None if value is None else json.dumps(value).encode(), method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)
envpath = root / 'litellm.env'
lines = [line for line in envpath.read_text().splitlines() if not line.startswith(('OLLAMA_API_KEY=', 'OLLAMA_API_BASE='))]
lines += ['OLLAMA_API_KEY=' + json.dumps(c['api_key']), 'OLLAMA_API_BASE=' + json.dumps(c['endpoint'])]
confpath = root / 'litellm.yaml'
conf = json.loads(confpath.read_text())
entries = {m['model_name']: m for m in conf['model_list']}
for model in models:
    entries[model] = {'model_name': model, 'litellm_params': {'model': 'openai/' + model, 'api_base': 'os.environ/OLLAMA_API_BASE', 'api_key': 'os.environ/OLLAMA_API_KEY'}}
conf['model_list'] = list(entries.values())
atomic(envpath, '\n'.join(lines) + '\n')
atomic(confpath, json.dumps(conf), 'aiagg-litellm')
subprocess.run(['systemctl', 'restart', 'ai-aggregator-litellm.service'], check=True)
env = {k: json.loads(v) for k, v in (line.split('=', 1) for line in envpath.read_text().splitlines() if '=' in line)}
for _ in range(30):
    try:
        call('http://127.0.0.1:4000/v1/models', {'Authorization': 'Bearer ' + env['LITELLM_MASTER_KEY']})
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit('LiteLLM readiness failed')
admin = json.loads((root / 'bootstrap.json').read_text())['gateway/new-api']
session = call('http://127.0.0.1:3000/api/user/login', {'Content-Type': 'application/json'}, {'username': admin['bootstrap_admin_username'], 'password': admin['bootstrap_admin_password']})['data']
headers = {'Authorization': 'Bearer ' + session['access_token'], 'New-Api-User': str(session['user']['id']), 'Content-Type': 'application/json'}
items = call('http://127.0.0.1:3000/api/channel/?p=0&size=100', headers)['data']['items']
channel = {'name': 'litellm-ollama-cloud', 'type': 1, 'status': 1, 'base_url': 'http://127.0.0.1:4000', 'key': env['LITELLM_MASTER_KEY'], 'models': ','.join(models), 'group': 'default', 'priority': 0, 'weight': 10}
existing = next((x for x in items if x['name'] == channel['name']), None)
if existing:
    channel['id'] = existing['id']
    # New API updates status through its dedicated endpoint, not channel PUT.
    channel.pop('status')
    result = call('http://127.0.0.1:3000/api/channel/', headers, channel, 'PUT')
else:
    result = call('http://127.0.0.1:3000/api/channel/', headers, {'mode': 'single', 'channel': channel}, 'POST')
if not result.get('success'):
    raise SystemExit('New API channel registration failed')
# Persist only model IDs; runtime refresh retrieves the key using the host identity.
cfgpath = pathlib.Path('/etc/ai-aggregator/home-lab.json')
cfg = json.loads(cfgpath.read_text())
cfg['ollama_cloud_models'] = models
atomic(cfgpath, json.dumps(cfg, indent=2) + '\n')
p = pathlib.Path('/opt/ai-aggregator/bootstrap/vault-runtime.py')
source = p.read_text()
marker = '    # Ollama Cloud: optional verified models from host declaration'
if marker not in source:
    anchor = '    # JSON is valid YAML and avoids interpolation of secret characters.'
    if anchor not in source:
        raise SystemExit('Unexpected runtime renderer; persistence not updated')
    addition = """    # Ollama Cloud: optional verified models from host declaration
    if CFG.get('ollama_cloud_models'):
        oc = vault(CFG['vault_prefix'] + '/litellm/providers/ollama', token)['data']['data']
        current = dict(line.split('=', 1) for line in (RUN / 'litellm.env').read_text().splitlines() if '=' in line)
        values = {key: json.loads(value) for key, value in current.items()}
        values.update(OLLAMA_API_KEY=oc['api_key'], OLLAMA_API_BASE=oc['endpoint'])
        write(RUN / 'litellm.env', env(values))
        for model in CFG['ollama_cloud_models']:
            models.append({'model_name': model, 'litellm_params': {'model': 'openai/' + model,
                'api_key': 'os.environ/OLLAMA_API_KEY', 'api_base': 'os.environ/OLLAMA_API_BASE'}})
"""
    candidate = source.replace(anchor, addition + anchor, 1)
    compile(candidate, str(p), 'exec')
    backup = p.with_suffix('.py.pre-ollama')
    if not backup.exists():
        atomic(backup, source)
    atomic(p, candidate)
print(json.dumps({'registered': models, 'channel': channel['name'], 'persistent_models': True}))
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', nargs='+', required=True)
    args = parser.parse_args()
    r = subprocess.run(['vault', 'kv', 'get', '-address=https://vault.svc.plus', '-format=json', 'kv/uat/ai-aggregator/litellm/providers/ollama'], capture_output=True, text=True, check=True)
    values = json.loads(r.stdout)['data']['data']
    if values.get('endpoint', '').rstrip('/') != 'https://ollama.com/v1' or not values.get('api_key'):
        raise SystemExit('Ollama Cloud credential contract incomplete')
    name = 'ai-aggregator-homelab-uat'
    old = subprocess.run(['vault', 'policy', 'read', '-address=https://vault.svc.plus', name], capture_output=True, text=True, check=True).stdout
    path = 'kv/data/uat/ai-aggregator/litellm/providers/ollama'
    if 'path "' + path + '"' not in old:
        subprocess.run(['vault', 'policy', 'write', '-address=https://vault.svc.plus', name, '-'], input=old + '\npath "' + path + '" { capabilities = ["read"] }\n', capture_output=True, text=True, check=True)
    payload = {'endpoint': values['endpoint'], 'api_key': values['api_key'], 'models': args.models}
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'root@10.79.0.7', 'python3 -c ' + shlex.quote(REMOTE)], input=json.dumps(payload), capture_output=True, text=True)
    if result.returncode:
        raise SystemExit('Remote Ollama stage failed; inspect host status without credentials')
    print(result.stdout.strip())

if __name__ == '__main__':
    main()
