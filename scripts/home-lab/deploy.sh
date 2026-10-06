#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
playbook_root="${AI_AGGREGATOR_PLAYBOOK_ROOT:-$repo_root/deploy/ansible}"
playbook="${AI_AGGREGATOR_PLAYBOOK:-$playbook_root/deploy_ai_aggregator.yaml}"
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

manifest_kind="$(python3 - "$manifest" <<'PY'
import sys
import yaml

with open(sys.argv[1], encoding="utf-8") as handle:
    document = yaml.safe_load(handle)
if not isinstance(document, dict):
    raise SystemExit("manifest root must be a mapping")
if document.get("schema_version") == "v1":
    print("gateway-contract")
elif document.get("kind") == "PersonalAIAggregator":
    print("gitops-deployment")
elif document.get("kind") == "UnifiedAIGateway":
    print("direct-transition")
else:
    raise SystemExit("unsupported manifest: expected gateway contract or AI Aggregator GitOps kind")
PY
)"

if [[ "$manifest_kind" == gateway-contract ]]; then
  (cd "$repo_root" && PYTHONPATH=. python3 -m gatewayctl validate "$manifest")
elif [[ "$manifest_kind" == direct-transition ]]; then
  [[ "${playbook##*/}" == deploy_ai_gateway_direct_new_api.yml ]] || {
    printf '%s\n' 'UnifiedAIGateway requires deploy_ai_gateway_direct_new_api.yml' >&2
    exit 2
  }
  [[ "$operation" == activate ]] || {
    printf '%s\n' 'UnifiedAIGateway direct transition is an apply operation; use --operation activate' >&2
    exit 2
  }
  printf 'accepted explicit direct-transition playbook: %s\n' "$playbook"
else
  printf 'accepted GitOps deployment manifest: %s\n' "$manifest"
fi

extra_args=()
if [[ -n "${AI_AGGREGATOR_LIMIT:-}" ]]; then
  extra_args+=(--limit "$AI_AGGREGATOR_LIMIT")
fi

if [[ "$manifest_kind" == direct-transition ]]; then
  ansible-playbook -i "$inventory" "$playbook" \
    -e "ai_gateway_manifest_file=$manifest" \
    "${extra_args[@]}"
else
  ansible-playbook -i "$inventory" "$playbook" \
    -e "ai_aggregator_manifest_file=$manifest" \
    -e "ai_aggregator_operation=$operation" \
    "${extra_args[@]}"
fi
