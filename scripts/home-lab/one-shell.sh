#!/usr/bin/env bash
set -euo pipefail

# Safe curl | bash entrypoint.
# With no options it deploys the declared Home-Lab default target. Advanced
# targets must provide explicit network/domain options or inventory/manifest.

usage() {
  cat <<'EOF'
Usage:
  curl -fsSL <pinned-raw-url> | bash

Options:
  --ref REF              Git tag or commit to clone (required for CI/production)
  --install-dir DIR      Destination directory
  --operation OP         plan, stage, or activate (default: activate)
  --inventory FILE       Ansible inventory; required for deployment
  --manifest FILE        GitOps manifest; required for deployment
  --playbook FILE        Explicit Ansible playbook (required for UnifiedAIGateway)
  --domain HOST           Generate a single-node manifest for this hostname
  --target-ip IP          SSH/local service address for generated target
  --dns-ip IP             DNS address; required separately for private-nat
  --network-mode MODE     public, private-nat, or xconnect (default: xconnect)
  --ssh-user USER         SSH user for generated inventory (default: root)
  --ssh-port PORT         SSH port for generated inventory (default: 22)
  --tls-mode MODE         automatic or runtime-files
  --target-dir DIR        Generated inventory/manifest directory
  --limit GROUP          Optional Ansible --limit value
  -h, --help             Show this help

No-option default:
  domain=ai-internal.onwalk.net
  target-ip=10.79.0.7
  network-mode=xconnect
  operation=activate

Use --operation plan for a non-mutating generated-target review.

The script never accepts, reads, or prints a client token. Credentials are
loaded by the deployment role from Vault or by the client credential store.
EOF
}

repo="ai-workspace-services/ai-aggregato-Gateway"
ref="${AI_AGGREGATOR_REF:-}"
install_dir="${AI_AGGREGATOR_INSTALL_DIR:-${HOME}/.local/share/ai-aggregato-Gateway}"
operation="${AI_AGGREGATOR_OPERATION:-activate}"
inventory="${AI_AGGREGATOR_INVENTORY:-}"
manifest="${AI_AGGREGATOR_MANIFEST:-}"
playbook="${AI_AGGREGATOR_PLAYBOOK:-}"
domain="${AI_AGGREGATOR_DOMAIN:-ai-internal.onwalk.net}"
target_ip="${AI_AGGREGATOR_TARGET_IP:-10.79.0.7}"
dns_ip="${AI_AGGREGATOR_DNS_IP:-}"
network_mode="${AI_AGGREGATOR_NETWORK_MODE:-xconnect}"
ssh_user="${AI_AGGREGATOR_SSH_USER:-root}"
ssh_port="${AI_AGGREGATOR_SSH_PORT:-22}"
tls_mode="${AI_AGGREGATOR_TLS_MODE:-}"
target_dir="${AI_AGGREGATOR_TARGET_DIR:-}"
limit="${AI_AGGREGATOR_LIMIT:-}"
generated_target=false

while (($#)); do
  case "$1" in
    --ref) ref="${2:?missing value for --ref}"; shift 2 ;;
    --install-dir) install_dir="${2:?missing value for --install-dir}"; shift 2 ;;
    --operation) operation="${2:?missing value for --operation}"; shift 2 ;;
    --inventory) inventory="${2:?missing value for --inventory}"; shift 2 ;;
    --manifest) manifest="${2:?missing value for --manifest}"; shift 2 ;;
    --playbook) playbook="${2:?missing value for --playbook}"; shift 2 ;;
    --domain) domain="${2:?missing value for --domain}"; shift 2 ;;
    --target-ip) target_ip="${2:?missing value for --target-ip}"; shift 2 ;;
    --dns-ip) dns_ip="${2:?missing value for --dns-ip}"; shift 2 ;;
    --network-mode) network_mode="${2:?missing value for --network-mode}"; shift 2 ;;
    --ssh-user) ssh_user="${2:?missing value for --ssh-user}"; shift 2 ;;
    --ssh-port) ssh_port="${2:?missing value for --ssh-port}"; shift 2 ;;
    --tls-mode) tls_mode="${2:?missing value for --tls-mode}"; shift 2 ;;
    --target-dir) target_dir="${2:?missing value for --target-dir}"; shift 2 ;;
    --limit) limit="${2:?missing value for --limit}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$operation" in
  plan|stage|activate) ;;
  *) printf '%s\n' '--operation must be plan, stage, or activate' >&2; exit 2 ;;
esac

command -v git >/dev/null 2>&1 || { printf 'git is required\n' >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { printf 'python3 is required\n' >&2; exit 1; }

if [[ -z "$ref" ]]; then
  printf '%s\n' 'set AI_AGGREGATOR_REF or pass --ref with a reviewed tag/commit' >&2
  exit 2
fi

if [[ -e "$install_dir" ]]; then
  printf 'install directory already exists: %s\n' "$install_dir" >&2
  printf '%s\n' 'choose another --install-dir or remove the directory manually' >&2
  exit 1
fi

mkdir -p "$(dirname -- "$install_dir")"
git clone --depth 1 --branch "$ref" "https://github.com/${repo}.git" "$install_dir"

"$install_dir/scripts/home-lab/install.sh"

if [[ -n "$domain" || -n "$target_ip" || -n "$dns_ip" ]]; then
  [[ -n "$domain" && -n "$target_ip" ]] || {
    printf '%s\n' '--domain and --target-ip are required together' >&2
    exit 2
  }
  [[ -z "$inventory" && -z "$manifest" ]] || {
    printf '%s\n' 'generated target options cannot be combined with --inventory/--manifest' >&2
    exit 2
  }
  target_dir="${target_dir:-$install_dir/targets/$(printf '%s' "$domain" | tr '.:' '__')}"
  render_args=(
    --domain "$domain"
    --target-ip "$target_ip"
    --network-mode "$network_mode"
    --ssh-user "$ssh_user"
    --ssh-port "$ssh_port"
    --output-dir "$target_dir"
  )
  [[ -n "$dns_ip" ]] && render_args+=(--dns-ip "$dns_ip")
  [[ -n "$tls_mode" ]] && render_args+=(--tls-mode "$tls_mode")
  python3 "$install_dir/scripts/home-lab/render-target.py" "${render_args[@]}"
  inventory="$target_dir/inventory.ini"
  manifest="$target_dir/ai-gateway-unified.yaml"
  [[ -n "$playbook" ]] || playbook="$install_dir/deploy/ansible/deploy_ai_gateway_direct_new_api.yml"
  generated_target=true
fi

if [[ "$generated_target" == true && "$operation" != activate ]]; then
  printf '%s\n' 'Target files were generated; no remote deployment was executed.'
  printf 'Review: %s\n' "$manifest"
  printf 'Next: rerun with --operation activate after DNS, TLS, Vault, and host checks.\n'
  exit 0
fi

if [[ -n "$inventory" || -n "$manifest" || -n "$playbook" ]]; then
  [[ -n "$inventory" && -n "$manifest" ]] || {
    printf '%s\n' '--inventory and --manifest must be provided together' >&2
    exit 2
  }
  export AI_AGGREGATOR_INVENTORY="$inventory"
  export AI_AGGREGATOR_MANIFEST="$manifest"
  export AI_AGGREGATOR_OPERATION="$operation"
  [[ -n "$playbook" ]] && export AI_AGGREGATOR_PLAYBOOK="$playbook"
  [[ -n "$limit" ]] && export AI_AGGREGATOR_LIMIT="$limit"
  "$install_dir/scripts/home-lab/deploy.sh"
else
  printf '%s\n' 'Installation complete; no deployment was executed.'
  printf 'Next: AI_AGGREGATOR_INVENTORY=... AI_AGGREGATOR_MANIFEST=... %s\n' \
    "AI_AGGREGATOR_OPERATION=plan $install_dir/scripts/home-lab/deploy.sh"
fi
