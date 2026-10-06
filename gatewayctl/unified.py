"""Stage authenticated model routing into an existing Standalone bundle.

Run on the gateway after Vault bootstrap. Credentials stay in tmpfs; this
module deliberately never prints a route bundle or a credential value.
"""
from __future__ import annotations

import argparse
import copy
import ipaddress
import json
import os
import re
import tempfile
from pathlib import Path

import yaml

HOST = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)+$")


def validate(spec: dict) -> None:
    def reject_secrets(value):
        if isinstance(value, dict):
            forbidden = {"api_key", "apikey", "password", "oauth_token", "refresh_token",
                         "access_token", "private_key", "session_secret", "crypto_secret"}
            if any(str(k).lower().replace('-', '_') in forbidden for k in value):
                raise ValueError("sensitive fields must not enter the model contract")
            for child in value.values():
                reject_secrets(child)
        elif isinstance(value, list):
            for child in value:
                reject_secrets(child)
    reject_secrets(spec)
    if not HOST.fullmatch(spec.get("host", "")):
        raise ValueError("host: invalid hostname")
    if spec.get("cross_backend_fallback") is not False:
        raise ValueError("cross_backend_fallback must be false")
    new_api = spec.get("new_api", {})
    try:
        new_api_ip = ipaddress.ip_address(new_api.get("bind_address", ""))
    except ValueError as exc:
        raise ValueError("new_api.bind_address must be private") from exc
    if not (new_api_ip.is_loopback or new_api_ip.is_private) or new_api_ip.is_unspecified:
        raise ValueError("new_api.bind_address must be private")
    if type(new_api.get("port")) is not int or not 0 < new_api["port"] < 65536:
        raise ValueError("new_api.port is invalid")
    if "models" in spec or "backends" in spec:
        raise ValueError("model catalog and provider channels belong to New API, not APISIX ingress GitOps")


def stage(bundle: dict, runtime: dict, spec: dict, credentials: dict | None = None) -> tuple[dict, dict]:
    """Render APISIX ingress to New API; New API owns token validation and billing.

    ``credentials`` remains accepted for callers from the previous renderer but
    is intentionally unused: no user, CPA, or LiteLLM secret is embedded here.
    """
    validate(spec)
    bundle, runtime = copy.deepcopy(bundle), copy.deepcopy(runtime)
    bases = {r["id"]: r for r in bundle.get("routes", [])}
    base = bases.get("security-base") or bases.get("unified-ai-gateway") or bases.get("new-api")
    required = {"ip-restriction", "limit-count"}
    if not base or not required <= base.get("plugins", {}).keys():
        raise ValueError("authenticated security policy is missing")
    new_api = spec["new_api"]
    host, port = new_api["bind_address"], new_api["port"]

    source_ip_policy = base["plugins"].get("ip-restriction")
    if not source_ip_policy.get("whitelist"):
        raise ValueError("New API console requires the existing explicit VPN allowlist")
    limit_policy = copy.deepcopy(base["plugins"]["limit-count"])
    # key-auth consumers do not exist in the New API token source of truth;
    # enforce a coarse per-client-IP burst ceiling at APISIX instead.
    limit_policy["key"] = "remote_addr"
    limit_policy["key_type"] = "var"
    limit_policy.setdefault("policy", "local")
    limit_policy.setdefault("rejected_code", 429)

    normalize_auth = """return function(conf, ctx)
 local headers = ngx.req.get_headers()
 local auth = headers['Authorization'] or headers['authorization']
 if auth and auth ~= '' then return end
 local key = headers['x-api-key'] or headers['X-API-Key'] or headers['apikey']
 if key and key ~= '' then
   ngx.req.set_header('Authorization', 'Bearer ' .. key)
 end
end"""
    route = {
        "id": "unified-ai-gateway",
        "host": spec["host"],
        "uri": "/v1/*",
        "priority": 200,
        "upstream": {
            "type": "roundrobin",
            "scheme": "http",
            "pass_host": "pass",
            "nodes": {f"{host}:{port}": 1},
            "timeout": {"connect": 5, "send": 120, "read": 120},
        },
        "plugins": {
            "forward-auth": {
                "uri": f"http://{host}:{port}/api/usage/token",
                "request_method": "GET",
                "request_headers": ["Authorization"],
                "timeout": 5000,
                "allow_degradation": False,
                "status_on_error": 503,
            },
            "ip-restriction": copy.deepcopy(source_ip_policy),
            "limit-count": limit_policy,
            "serverless-pre-function": {
                "phase": "rewrite",
                "functions": [normalize_auth],
            },
        },
    }
    if "real-ip" in base.get("plugins", {}):
        route["plugins"]["real-ip"] = copy.deepcopy(base["plugins"]["real-ip"])

    # Keep the first-party console on the same host. Its assets and management
    # API are private to the VPN allowlist and still require New API sessions.
    console_route = {
        "id": "new-api-console",
        "host": spec["host"],
        "uri": "/*",
        "priority": 1,
        "upstream": {
            "type": "roundrobin",
            "scheme": "http",
            "pass_host": "pass",
            "nodes": {f"{host}:{port}": 1},
            "timeout": {"connect": 5, "send": 30, "read": 60},
        },
        "plugins": {"ip-restriction": copy.deepcopy(source_ip_policy)},
    }
    if "real-ip" in base.get("plugins", {}):
        console_route["plugins"]["real-ip"] = copy.deepcopy(base["plugins"]["real-ip"])

    bundle["routes"] = [route, console_route]
    if "forward-auth" not in runtime["plugins"]:
        runtime["plugins"].append("forward-auth")
    if "serverless-pre-function" not in runtime["plugins"]:
        runtime["plugins"].append("serverless-pre-function")
    return bundle, runtime


def atomic_write(path: Path, value: dict) -> None:
    original = path.stat() if path.exists() else None
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".unified-")
    try:
        os.fchmod(fd, (original.st_mode & 0o777) if original else 0o600)
        if original:
            os.fchown(fd, original.st_uid, original.st_gid)
        with os.fdopen(fd, "w") as stream:
            stream.write(yaml.safe_dump(value, sort_keys=False))
            if path.name == "apisix.yaml":
                stream.write("#END\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--routes-file", type=Path)
    parser.add_argument("--runtime-file", type=Path)
    parser.add_argument("--seed-file", type=Path)
    parser.add_argument("--export-seed", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        spec = yaml.safe_load(args.manifest.read_text())["spec"]
        validate(spec)
        if args.export_seed:
            source = yaml.safe_load(args.routes_file.read_text())
            base = next(r for r in source['routes'] if r['id'] in {'new-api', 'unified-ai-gateway', 'security-base'})
            names = {'ip-restriction', 'limit-count', 'real-ip', 'serverless-pre-function'}
            seed = {'routes': [{'id': 'security-base', 'plugins': {
                k: v for k, v in base['plugins'].items() if k in names}}],
                'consumers': [{'username': c['username']} for c in source['consumers']]}
            atomic_write(args.export_seed, seed)
            print('non-sensitive security seed saved')
            return
        if args.validate_only:
            print("unified gateway contract valid")
            return
        if not args.routes_file or not args.runtime_file:
            raise ValueError("runtime files are required")
        bundle = yaml.safe_load((args.seed_file or args.routes_file).read_text())
        bundle, runtime = stage(bundle, yaml.safe_load(args.runtime_file.read_text()), spec)
        atomic_write(args.runtime_file, runtime)
        atomic_write(args.routes_file, bundle)
        print("unified gateway policy staged; credentials were not displayed")
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError):
        # Parsing exceptions may contain secret source lines. Do not print them.
        raise SystemExit("unified gateway validation/staging failed; check contract and runtime prerequisites")


if __name__ == "__main__":
    main()
