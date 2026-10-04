#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
playbook_root="${AI_AGGREGATOR_PLAYBOOK_ROOT:-$repo_root/deploy/ansible}"
playbook="$playbook_root/deploy_ai_aggregator.yaml"
operation="${AI_AGGREGATOR_OPERATION:-plan}"
inventory="${AI_AGGREGATOR_INVENTORY:?set AI_AGGREGATOR_INVENTORY to an inventory file}"
manifest="${AI_AGGREGATOR_MANIFEST:?set AI_AGGREGATOR_MANIFEST to a checked-out GitOps manifest}"

case "$operation" in
  plan|stage|activate) ;;
  *) printf 'AI_AGGREGATOR_OPERATION must be plan, stage, or activate\n' >&2; exit 2 ;;
esac

[[ -r "$inventory" ]] || { printf 'inventory is not readable: %s\n' "$inventory" >&2; exit 1; }
[[ -r "$manifest" ]] || { printf 'manifest is not readable: %s\n' "$manifest" >&2; exit 1; }
[[ -r "$playbook" ]] || { printf 'playbook is not readable: %s\n' "$playbook" >&2; exit 1; }

(cd "$repo_root" && PYTHONPATH=. python3 -m gatewayctl validate "$manifest")

extra_args=()
if [[ -n "${AI_AGGREGATOR_LIMIT:-}" ]]; then
  extra_args+=(--limit "$AI_AGGREGATOR_LIMIT")
fi

ansible-playbook -i "$inventory" "$playbook" \
  -e "ai_aggregator_manifest_file=$manifest" \
  -e "ai_aggregator_operation=$operation" \
  "${extra_args[@]}"
