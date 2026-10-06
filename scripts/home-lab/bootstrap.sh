#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

required=(python3 curl ssh)
for command_name in "${required[@]}"; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'missing required command: %s\n' "$command_name" >&2
    exit 1
  }
done

if [[ "${AI_AGGREGATOR_REQUIRE_ANSIBLE:-true}" == "true" ]]; then
  command -v ansible-playbook >/dev/null 2>&1 || {
    printf 'missing required command: ansible-playbook\n' >&2
    exit 1
  }
fi

manifest="${AI_AGGREGATOR_MANIFEST:-$repo_root/contracts/gateway.yaml}"
if [[ -f "$manifest" ]]; then
  (cd "$repo_root" && PYTHONPATH=. python3 -m gatewayctl validate "$manifest")
else
  printf 'manifest not found; set AI_AGGREGATOR_MANIFEST for deployment validation\n' >&2
fi

printf 'AI Aggregator prerequisites are present. No credentials were read or written.\n'
